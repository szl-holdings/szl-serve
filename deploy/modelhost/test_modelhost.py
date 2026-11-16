"""Contract, file-integrity and real HTTP tests without Torch or remote services."""
import contextlib
import copy
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from szl_modelhost import (BoundedHTTPServer, ModelHost, ServeError, TorchBackend,
                           fingerprint, verify_files)
from contract import ContractError


class FakeBackend:
    def __init__(self):
        self.loaded_bases = []
        self.aliases = []
        self.error = None
        self.entered = self.release = None
        self.cleanup_calls = 0

    def free_vram_mb(self):
        return 50000

    def gpu_name(self):
        return "Mock GPU"

    def load_base(self, spec):
        self.loaded_bases.append((spec["repo"], spec["revision"]))
        return {"base": spec["revision"]}

    def load_adapter(self, base, spec, alias):
        self.aliases.append(alias)
        return {**base, "alias": alias}

    def generate(self, handle, prompt, count, max_input, max_time):
        if self.entered:
            self.entered.set()
            if not self.release.wait(5):
                raise RuntimeError("test release not signaled")
        if self.error:
            raise self.error
        return {"generation": "ok", "input_tokens": 6, "output_tokens": count,
                "duration_ms": 1.0}

    def is_oom(self, exc):
        return isinstance(exc, MemoryError)

    def cleanup(self):
        self.cleanup_calls += 1


def inventory(directory):
    return [{"path": p.name, "size": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(directory.iterdir()) if p.is_file()]


class Fixture:
    def setup_fixture(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        base_dir = self.root / "base"
        base_dir.mkdir()
        (base_dir / "config.json").write_text("{}")
        (base_dir / "model.safetensors").write_bytes(b"base weights")
        base = {"repo": "test/base", "revision": "a" * 40, "path": str(base_dir),
                "files": inventory(base_dir), "estimated_vram_mb": 900}
        self.lock = {"schema": "szl.modelhost-lock/v2", "host_label": "test-host",
                     "manifest": ["test/model.a", "test/model_a"],
                     "intentional_exclusions": {}, "bases": {"opaque-key": base}, "models": {}}
        for name in ("model.a", "model_a"):
            path = self.root / name
            path.mkdir()
            (path / "adapter_config.json").write_text('{"base_model_name_or_path":"test/base"}')
            (path / "adapter_model.safetensors").write_bytes(name.encode())
            spec = {"name": name, "repo": "test/" + name, "revision": "b" * 40,
                    "kind": "lora", "adapter_config": "release/adapter_config.json",
                    "path": str(path), "files": inventory(path), "base_key": "opaque-key",
                    "status": "pinned"}
            spec["artifact_fingerprint"] = fingerprint(spec, base)
            self.lock["models"][name] = spec
        self.config = {"host_label": "test-host", "manifest": self.lock["manifest"],
                       "min_free_disk_bytes": 0, "reserve_mb": 4000,
                       "receipt_path": str(self.root / "receipts" / "latest.json"),
                       "max_queue": 0, "max_http_workers": 1}
        self.backend = FakeBackend()
        self.log = io.StringIO()

    def host(self, initialize=True):
        instance = ModelHost(self.config, self.lock, backend=self.backend)
        if initialize:
            with contextlib.redirect_stdout(self.log):
                instance.initialize()
        return instance


class ModelHostTests(Fixture, unittest.TestCase):
    def setUp(self):
        self.setup_fixture()

    def tearDown(self):
        self.temp.cleanup()

    def test_import_has_no_tensor_or_config_side_effects(self):
        result = subprocess.run([sys.executable, "-c",
            "import sys,szl_modelhost; assert 'torch' not in sys.modules"],
            cwd=Path(__file__).parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_base_shared_and_aliases_do_not_collide(self):
        host = self.host()
        self.assertEqual(len(self.backend.loaded_bases), 1)
        self.assertEqual(set(host.bases), {"test/base@" + "a" * 40})
        self.assertEqual(len(set(self.backend.aliases)), 2)
        self.assertTrue(all("." not in alias for alias in self.backend.aliases))
        self.assertTrue(host.readiness()["ready"])

    def test_base_revision_is_part_of_pool_identity(self):
        base2 = copy.deepcopy(self.lock["bases"]["opaque-key"])
        base2["revision"] = "c" * 40
        self.lock["bases"]["second"] = base2
        spec = self.lock["models"]["model_a"]
        spec["base_key"] = "second"
        spec["artifact_fingerprint"] = fingerprint(spec, base2)
        host = self.host()
        self.assertEqual(len(host.bases), 2)
        self.assertEqual(len(self.backend.loaded_bases), 2)

    def test_adapter_tamper_never_reaches_loader(self):
        spec = self.lock["models"]["model.a"]
        (Path(spec["path"]) / "adapter_model.safetensors").write_bytes(b"tampered")
        host = self.host()
        self.assertNotIn("model.a", host.handles)
        self.assertEqual(host.states["model.a"]["reason"], "artifact_hash_mismatch")
        self.assertFalse(host.readiness()["ready"])

    def test_fingerprint_mismatch_rejected(self):
        self.lock["models"]["model.a"]["artifact_fingerprint"] = "0" * 64
        host = self.host()
        self.assertEqual(host.states["model.a"]["reason"], "artifact_fingerprint_mismatch")
        self.assertNotIn("model.a", host.handles)

    def test_incorrectly_paired_base_rejected_even_when_hashes_match(self):
        spec = self.lock["models"]["model.a"]
        (Path(spec["path"]) / "adapter_config.json").write_text('{"base_model_name_or_path":"test/wrong-base"}')
        spec["files"] = inventory(Path(spec["path"]))
        spec["artifact_fingerprint"] = fingerprint(spec, self.lock["bases"]["opaque-key"])
        host = self.host()
        self.assertEqual(host.states["model.a"]["reason"], "adapter_base_mismatch")
        self.assertNotIn("model.a", host.handles)

    def test_file_change_during_verification_rejected(self):
        spec = self.lock["models"]["model.a"]
        def hash_then_modify(path):
            value = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            with open(path, "ab") as stream:
                stream.write(b"changed")
            return value
        with mock.patch("szl_modelhost.sha256_file", side_effect=hash_then_modify):
            with self.assertRaises(ContractError) as error:
                verify_files(spec)
        self.assertEqual(error.exception.code, "artifact_changed")

    def test_base_tamper_fails_all_dependents_without_load(self):
        base = self.lock["bases"]["opaque-key"]
        (Path(base["path"]) / "config.json").write_text('{"changed": true}')
        host = self.host()
        self.assertEqual(host.handles, {})
        self.assertEqual(self.backend.loaded_bases, [])

    def test_traversal_in_locked_file_rejected(self):
        base = copy.deepcopy(self.lock["bases"]["opaque-key"])
        base["files"][0]["path"] = "../config.json"
        with self.assertRaises(ContractError) as error:
            verify_files(base)
        self.assertEqual(error.exception.code, "invalid_artifact_path")

    def test_canary_receipt_omits_content_and_is_private(self):
        host = self.host()
        receipt = Path(host.receipt_path)
        self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)
        rec = json.loads(receipt.read_text())
        self.assertEqual(rec["loaded"], ["model.a", "model_a"])
        self.assertEqual(rec["statuses"], {"model.a": "loaded", "model_a": "loaded"})
        self.assertEqual(rec["free_mb"], 50000)
        self.assertEqual(rec["gpu"], "Mock GPU")
        canary = rec["models"]["model.a"]["canary"]
        self.assertEqual(canary["output_tokens"], 1)
        self.assertEqual(canary["output_sha256"], hashlib.sha256(b"ok").hexdigest())
        self.assertNotIn("generation", canary)
        self.assertNotIn("prompt", receipt.read_text())
        self.assertTrue(canary["operational_only"])

    def test_expired_canary_degrades_readiness_not_liveness(self):
        host = self.host()
        host.states["model.a"]["canary_monotonic"] -= host.canary_max_age_s + 1
        self.assertFalse(host.readiness()["ready"])
        self.assertTrue(host.health()["alive"])
        self.assertEqual(host.states["model.a"]["status"], "loaded")

    def test_canary_failure_retains_residency(self):
        self.backend.error = RuntimeError("secret-must-never-be-logged")
        host = self.host()
        self.assertEqual(len(host.handles), 2)
        self.assertFalse(host.readiness()["ready"])
        self.assertNotIn("secret-must-never-be-logged", self.log.getvalue())

    def test_exclusions_preserve_full_manifest(self):
        self.lock["intentional_exclusions"]["model_a"] = "metadata_only_no_weights"
        host = self.host()
        ready = host.readiness()
        self.assertTrue(ready["ready"])
        self.assertEqual(ready["configured_count"], 2)
        self.assertEqual(ready["required_count"], 1)
        self.assertEqual(host.model_catalog()["models"]["model_a"]["status"], "excluded")

    def test_generation_error_releases_admission_and_sanitizes(self):
        host = self.host()
        self.backend.error = MemoryError("credential-private")
        with contextlib.redirect_stdout(self.log):
            with self.assertRaises(ServeError) as error:
                host.generate({"model": "model.a", "prompt": "private-prompt", "max_new_tokens": 1})
        self.assertEqual(error.exception.code, "generation_oom")
        self.assertEqual(host.gate.snapshot()["active"], 0)
        self.assertNotIn("credential-private", self.log.getvalue())
        self.assertNotIn("private-prompt", self.log.getvalue())
        self.backend.error = None
        with contextlib.redirect_stdout(self.log):
            self.assertEqual(host.generate({"model": "model.a", "prompt": "x"})["generation"], "ok")

    def test_concurrent_generation_is_bounded(self):
        host = self.host()
        self.backend.entered, self.backend.release = threading.Event(), threading.Event()
        errors = []
        def run():
            try:
                host.generate({"model": "model.a", "prompt": "x", "max_new_tokens": 1})
            except Exception as exc:
                errors.append(exc)
        with contextlib.redirect_stdout(self.log):
            first = threading.Thread(target=run)
            first.start()
            self.assertTrue(self.backend.entered.wait(2))
            with self.assertRaises(ServeError) as error:
                host.generate({"model": "model_a", "prompt": "y"})
            self.assertEqual(error.exception.code, "busy")
            self.backend.release.set()
            first.join(3)
        self.assertFalse(first.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(host.gate.snapshot()["active"], 0)

    def test_load_adapter_supports_both_library_signatures(self):
        class Old:
            def load_adapter(self, path, adapter_name=None, adapter_kwargs=None):
                self.options = adapter_kwargs
            def eval(self):
                pass
        class New:
            def load_adapter(self, path, adapter_name=None, local_files_only=False):
                self.options = {"local_files_only": local_files_only}
            def eval(self):
                pass
        backend = TorchBackend.__new__(TorchBackend)
        for cls in (Old, New):
            model = cls()
            backend.load_adapter({"model": model}, {"path": "/local/adapter"}, "alias")
            self.assertEqual(model.options, {"local_files_only": True})


class ObservedServer(BoundedHTTPServer):
    def __init__(self, address, host):
        self.worker_started = threading.Event()
        super().__init__(address, host)

    def process_request_thread(self, request, client_address):
        self.worker_started.set()
        super().process_request_thread(request, client_address)


class HTTPTests(Fixture, unittest.TestCase):
    def setUp(self):
        self.setup_fixture()
        self.config["origin_auth_token"] = "test-origin-token"
        self.instance = self.host()
        self.server = ObservedServer(("127.0.0.1", 0), self.instance)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        request_headers = {"Authorization": "Bearer test-origin-token", "Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        status, data = response.status, json.loads(response.read())
        connection.close()
        return status, data

    def test_health_is_not_readiness(self):
        self.instance.states["model.a"]["canary_ok"] = False
        self.assertEqual(self.request("GET", "/health")[0], 200)
        self.assertEqual(self.request("GET", "/ready")[0], 503)

    def test_auth_protects_catalog_and_generation(self):
        self.assertEqual(self.request("GET", "/models", headers={"Authorization": "Bearer wrong"})[0], 401)
        self.assertEqual(self.request("POST", "/generate", "{}", {"Authorization": "Bearer wrong"})[0], 401)
        self.assertEqual(self.request("GET", "/health", headers={"Authorization": "Bearer wrong"})[0], 200)

    def test_generation_success_includes_identity(self):
        with contextlib.redirect_stdout(self.log):
            status, data = self.request("POST", "/generate", json.dumps({"model": "model.a", "prompt": "x", "max_new_tokens": 1}))
        self.assertEqual(status, 200)
        self.assertEqual(data["generation"], "ok")
        self.assertEqual(data["artifact_fingerprint"], self.lock["models"]["model.a"]["artifact_fingerprint"])
        self.assertEqual(data["repo"], "test/model.a")
        self.assertEqual(data["revision"], "b" * 40)
        self.assertEqual(data["completion_tokens"], 1)
        self.assertEqual(data["elapsed_ms"], 1.0)

    def test_expected_identity_rejects_before_generation(self):
        self.backend.error = RuntimeError("generation must not run")
        body = {"model": "model.a", "prompt": "x", "expected_artifact_fingerprint": "0" * 64}
        status, data = self.request("POST", "/generate", json.dumps(body))
        self.assertEqual(status, 409)
        self.assertEqual(data["err"], "artifact_identity_mismatch")
        self.assertEqual(self.instance.stats["requests"], 0)
        body["expected_artifact_fingerprint"] = True
        self.assertEqual(self.request("POST", "/generate", json.dumps(body))[0], 400)
        body["expected_artifact_fingerprint"] = None
        self.assertEqual(self.request("POST", "/generate", json.dumps(body))[0], 400)

    def test_matching_expected_identity_generates(self):
        body = {"model": "model.a", "prompt": "x", "max_new_tokens": 1,
                "expected_artifact_fingerprint": self.lock["models"]["model.a"]["artifact_fingerprint"]}
        with contextlib.redirect_stdout(self.log):
            self.assertEqual(self.request("POST", "/generate", json.dumps(body))[0], 200)

    def test_strict_request_bounds(self):
        for body, expected in (("[]", 400), ('{"model":"model.a","prompt":"x","max_new_tokens":true}', 400),
                               ('{"model":"model.a","prompt":"x","max_new_tokens":257}', 400),
                               (json.dumps({"model": "model.a", "prompt": "x" * 16385}), 413),
                               ("{", 400)):
            with self.subTest(expected=expected):
                self.assertEqual(self.request("POST", "/generate", body)[0], expected)

    def test_oversized_body_rejected_before_read(self):
        self.assertEqual(self.request("POST", "/generate", "{}", {"Content-Length": "65537"})[0], 413)

    def test_content_type_required(self):
        self.assertEqual(self.request("POST", "/generate", "{}", {"Content-Type": "text/plain"})[0], 415)

    def test_worker_limit_rejects_without_new_worker(self):
        self.server.worker_started.clear()
        held = socket.create_connection(self.server.server_address, timeout=2)
        try:
            held.sendall(b"GET /health HTTP/1.0\r\n")
            self.assertTrue(self.server.worker_started.wait(2))
            status, data = self.request("GET", "/health")
            self.assertEqual(status, 503)
            self.assertEqual(data["err"], "http_workers_busy")
        finally:
            held.close()


if __name__ == "__main__":
    unittest.main()
