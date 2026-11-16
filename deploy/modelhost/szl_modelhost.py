#!/usr/bin/env python3
"""Pinned, cache-only SZL model host with bounded serving and evidence receipts.

Importing this module does not load configuration, contact a network, or import
Torch.  The HTTP listener is intended to sit behind the authenticated origin
route.  Operational canaries establish execution, never model quality.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gc
import hashlib
import hmac
import inspect
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from contract import (AdmissionRejected, BoundedAdmission, ContractError,
                      readiness_summary, validate_generation_request)

MIB = 1024 ** 2
GIB = 1024 ** 3
SCHEMA = "szl.modelhost/v2"


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def event(code, **fields):
    """Write only allowlisted metadata passed by callers, never exception text."""
    print(json.dumps({"clock_utc": utc_now(), "event": code, **fields},
                     sort_keys=True), flush=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(8 * MIB), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(model, base):
    payload = {"repo": model["repo"], "revision": model["revision"],
               "adapter_config": model["adapter_config"], "files": model["files"],
               "base": {"repo": base["repo"], "revision": base["revision"],
                        "files": base["files"]}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def relative_file(path):
    if (not isinstance(path, str) or not path or "\\" in path or ":" in path
            or any(ord(c) < 32 or ord(c) == 127 for c in path)
            or any(p in ("", ".", "..") for p in path.split("/"))):
        raise ContractError("invalid_artifact_path", "Invalid artifact path")
    return path


def verify_files(spec):
    """Verify the selected directory only; HF cache blob symlinks are supported."""
    root = spec.get("path")
    files = spec.get("files")
    if not isinstance(root, str) or not os.path.isabs(root) or not isinstance(files, list) or not files:
        raise ContractError("invalid_artifact_files", "Missing pinned file identity")
    names = []
    for record in files:
        name = relative_file(record.get("path"))
        names.append(name)
        if (type(record.get("size")) is not int or record["size"] < 0
                or re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", ""))) is None):
            raise ContractError("invalid_artifact_files", "Invalid pinned file metadata")
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            raise ContractError("artifact_hash_mismatch", "Pinned artifact did not verify")
        before = os.stat(path)
        actual_sha256 = sha256_file(path)
        after = os.stat(path)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ContractError("artifact_changed", "Artifact changed while verifying")
        if before.st_size != record["size"] or not hmac.compare_digest(actual_sha256, record["sha256"]):
            raise ContractError("artifact_hash_mismatch", "Pinned artifact did not verify")
    if names != sorted(set(names)):
        raise ContractError("invalid_artifact_files", "Pinned files must be sorted and unique")
    if re.fullmatch(r"[0-9a-f]{40,64}", str(spec.get("revision", ""))) is None:
        raise ContractError("invalid_revision", "An immutable commit revision is required")


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(obj, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def integer_limit(config, key, default, minimum=1):
    value = config.get(key, default)
    if type(value) is not int or value < minimum:
        raise ContractError("invalid_config", "Invalid integer limit: " + key)
    return value


class ServeError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


class TorchBackend:
    """All loading is local and exact; no repository resolution or downloads."""
    def __init__(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.AutoModelForCausalLM, self.AutoTokenizer = AutoModelForCausalLM, AutoTokenizer

    def free_vram_mb(self):
        return self.torch.cuda.mem_get_info()[0] // MIB

    def gpu_name(self):
        return self.torch.cuda.get_device_name(0)

    def load_base(self, spec):
        tok = self.AutoTokenizer.from_pretrained(spec["path"], local_files_only=True,
                                               trust_remote_code=False)
        model = self.AutoModelForCausalLM.from_pretrained(
            spec["path"], local_files_only=True, trust_remote_code=False,
            torch_dtype=self.torch.bfloat16, device_map="cuda:0")
        model.eval()
        return {"model": model, "tok": tok}

    def load_adapter(self, base, spec, alias):
        load = base["model"].load_adapter
        parameters = inspect.signature(load).parameters
        # Current Transformers accepts the top-level flag but incorrectly sends
        # it to LoadStateDictConfig. adapter_kwargs targets download_kwargs and
        # works with both the older and current PEFT integrations.
        kwargs = ({"adapter_kwargs": {"local_files_only": True}} if "adapter_kwargs" in parameters
                  else {"local_files_only": True})
        load(spec["path"], adapter_name=alias, **kwargs)
        base["model"].eval()
        return {**base, "alias": alias}

    def generate(self, handle, prompt, max_new_tokens, max_input_tokens, max_time):
        model, tok = handle["model"], handle["tok"]
        enc = out = None
        start = time.monotonic()
        try:
            model.set_adapter(handle["alias"])
            has_chat_template = bool(getattr(tok, "chat_template", None))
            if has_chat_template:
                text = tok.apply_chat_template([{"role": "user", "content": prompt}],
                                               tokenize=False, add_generation_prompt=True)
            else:
                text = prompt
            enc = tok(text, return_tensors="pt", truncation=False,
                      add_special_tokens=not has_chat_template)
            input_tokens = int(enc["input_ids"].shape[1])
            context = getattr(model.config, "max_position_embeddings", None)
            if (input_tokens > max_input_tokens
                    or (type(context) is int and input_tokens + max_new_tokens > context)):
                raise ServeError(413, "input_tokens_exceeded")
            if input_tokens == 0:
                raise ServeError(400, "empty_tokenized_input")
            enc = enc.to("cuda:0")
            with self.torch.inference_mode():
                out = model.generate(**enc, max_new_tokens=max_new_tokens,
                                     max_time=max_time, do_sample=False,
                                     pad_token_id=tok.eos_token_id)
            output_tokens = int(out.shape[1]) - input_tokens
            generation = tok.decode(out[0][input_tokens:], skip_special_tokens=True)
            return {"generation": generation, "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "duration_ms": round((time.monotonic() - start) * 1000, 3)}
        finally:
            del enc, out

    def is_oom(self, exc):
        return isinstance(exc, self.torch.cuda.OutOfMemoryError)

    def cleanup(self):
        gc.collect()
        self.torch.cuda.empty_cache()


class ModelHost:
    def __init__(self, config, lock, *, lock_path=None, backend=None):
        self.config, self.lock = dict(config), lock
        if lock.get("schema") != "szl.modelhost-lock/v2":
            raise ContractError("invalid_lock_schema", "Unsupported model lock schema")
        self.manifest = lock.get("manifest", [])
        if config.get("manifest") is not None and config["manifest"] != self.manifest:
            raise ContractError("manifest_mismatch", "Config and pinned manifest differ")
        self.host_label = str(config.get("host_label", lock.get("host_label", "unknown")))
        if lock.get("host_label") != self.host_label:
            raise ContractError("host_mismatch", "Model lock belongs to another host")
        self.root = Path(lock_path).resolve().parent if lock_path else Path(__file__).resolve().parent
        self.lock_path = str(lock_path) if lock_path else None
        self.boot_id = str(uuid.uuid4())
        self.boot_utc = utc_now()
        self.started = time.monotonic()
        self.max_body_bytes = integer_limit(config, "max_body_bytes", 65536)
        self.max_prompt_chars = integer_limit(config, "max_prompt_chars", 16384)
        self.max_input_tokens = integer_limit(config, "max_input_tokens", 2048)
        self.max_new_tokens = integer_limit(config, "max_new_tokens", 256)
        self.reserve_mb = integer_limit(config, "reserve_mb", 6000, 0)
        self.min_free_disk_bytes = integer_limit(config, "min_free_disk_bytes", 50 * GIB, 0)
        self.socket_timeout_s = integer_limit(config, "socket_timeout_s", 10)
        self.queue_timeout_s = integer_limit(config, "queue_timeout_s", 2, 0)
        self.generation_max_time_s = integer_limit(config, "generation_max_time_s", 60)
        self.canary_max_age_s = integer_limit(config, "canary_max_age_s", 24 * 3600)
        self.canary_interval_s = integer_limit(config, "canary_interval_s", 6 * 3600)
        self.gate = BoundedAdmission(1, integer_limit(config, "max_queue", 2, 0))
        self.origin_auth_token = config.get("origin_auth_token")
        token_file = config.get("origin_auth_token_file")
        if token_file:
            self.origin_auth_token = Path(token_file).read_text(encoding="utf-8").strip()
        if self.origin_auth_token is not None and (not isinstance(self.origin_auth_token, str)
                                                 or not self.origin_auth_token):
            raise ContractError("invalid_origin_auth", "Origin token must be nonempty")
        self.backend = backend
        self.exclusions = dict(lock.get("intentional_exclusions", {}))
        self.states, self.handles, self.bases = {}, {}, {}
        self.state_lock = threading.RLock()
        self.initialization_complete = False
        self.shutdown_event = threading.Event()
        self.stats = {"requests": 0, "succeeded": 0, "failed": 0, "busy": 0,
                      "output_tokens": 0}
        self.receipt_path = str(config.get("receipt_path", self.root / "receipts" / "latest.json"))
        self.sources = {Path(__file__).name: sha256_file(__file__),
                        "contract.py": sha256_file(Path(__file__).with_name("contract.py"))}
        if lock_path:
            self.sources["model_lock.json"] = sha256_file(lock_path)
        # Validate denominator, duplicate model names and exclusions before loading.
        readiness_summary(self.manifest, {}, intentional_exclusions=self.exclusions)
        for repo in self.manifest:
            name = repo.rsplit("/", 1)[-1]
            spec = lock.get("models", {}).get(name, {})
            base = lock.get("bases", {}).get(spec.get("base_key"), {})
            if spec and (spec.get("repo") != repo or spec.get("name", name) != name):
                raise ContractError("model_identity_mismatch", "Model identity differs from manifest")
            self.states[name] = {"name": name, "repo": repo, "kind": spec.get("kind", "lora"),
                                 "status": "excluded" if name in self.exclusions else "pending",
                                 "revision": spec.get("revision"),
                                 "adapter_config": spec.get("adapter_config"),
                                 "base_key": spec.get("base_key"),
                                 "base": base.get("repo"), "base_revision": base.get("revision"),
                                 "artifact_fingerprint": spec.get("artifact_fingerprint"),
                                 "identity_verified": False, "canary_ok": False}
        if set(lock.get("models", {})) - set(self.states):
            raise ContractError("unexpected_lock_models", "Lock includes models outside manifest")

    def _fail(self, name, code, exc=None):
        with self.state_lock:
            self.states[name].update(status="unavailable", reason=code)
        event(code, model=name, **({"exception_type": type(exc).__name__} if exc else {}))

    def initialize(self):
        if self.backend is None:
            self.backend = TorchBackend()
        failed_bases = set()
        for name in sorted(self.states):
            if name in self.exclusions:
                continue
            spec = self.lock.get("models", {}).get(name, {})
            if spec.get("status") != "pinned":
                reason = spec.get("reason", "artifact_unavailable")
                self._fail(name, reason if re.fullmatch(r"[a-z_]{1,64}", str(reason)) else "artifact_unavailable")
                continue
            if spec.get("kind") != "lora":
                self._fail(name, "unsupported_model_kind")
                continue
            base_key = spec.get("base_key")
            base = self.lock.get("bases", {}).get(base_key)
            if not base or not base.get("repo") or not base.get("revision"):
                self._fail(name, "invalid_base_identity")
                continue
            pool_key = base["repo"] + "@" + base["revision"]
            if pool_key in failed_bases:
                self._fail(name, "base_unavailable")
                continue
            try:
                relative_file(spec["adapter_config"])
                if spec["adapter_config"].rsplit("/", 1)[-1] != "adapter_config.json":
                    raise ContractError("invalid_adapter_config", "Selected config is invalid")
                verify_files(spec)
                if "adapter_config.json" not in {f["path"] for f in spec["files"]}:
                    raise ContractError("adapter_config_missing", "Selected directory lacks pinned config")
                with open(os.path.join(spec["path"], "adapter_config.json"), encoding="utf-8") as stream:
                    adapter_config = json.load(stream)
                if adapter_config.get("base_model_name_or_path") != base["repo"]:
                    raise ContractError("adapter_base_mismatch", "Adapter and locked base differ")
                if not hmac.compare_digest(fingerprint(spec, base), spec.get("artifact_fingerprint", "")):
                    raise ContractError("artifact_fingerprint_mismatch", "Model identity did not verify")
                if pool_key not in self.bases:
                    try:
                        verify_files(base)
                    except Exception:
                        failed_bases.add(pool_key)
                        raise
                    need = base.get("estimated_vram_mb")
                    if type(need) is not int or need < 1:
                        raise ContractError("invalid_vram_estimate", "Base estimate is required")
                    if self.backend.free_vram_mb() < need + self.reserve_mb:
                        failed_bases.add(pool_key)
                        self._fail(name, "vram_base_reserve")
                        continue
                    try:
                        self.bases[pool_key] = self.backend.load_base(base)
                    except Exception:
                        failed_bases.add(pool_key)
                        raise
                # Adapter allocation follows its actual pinned weight size plus a small margin.
                weight_bytes = sum(f["size"] for f in spec["files"]
                                   if f["path"].endswith((".safetensors", ".bin", ".pt")))
                need = max(128, math.ceil(weight_bytes / MIB * 1.1) + 64)
                if self.backend.free_vram_mb() < need + self.reserve_mb:
                    self._fail(name, "vram_adapter_reserve")
                    continue
                alias = "m_" + hashlib.sha256((name + ":" + spec["artifact_fingerprint"]).encode()).hexdigest()[:32]
                self.handles[name] = self.backend.load_adapter(self.bases[pool_key], spec, alias)
                with self.state_lock:
                    self.states[name].update(status="loaded", identity_verified=True,
                                             adapter_alias=alias, loaded_utc=utc_now())
                event("model_loaded", model=name, free_mb=self.backend.free_vram_mb())
            except Exception as exc:
                code = exc.code if isinstance(exc, ContractError) else "model_load_failed"
                self._fail(name, code, exc)
                self._cleanup()
        for name in sorted(self.handles):
            with self.gate.slot():
                self._canary(name)
        self.initialization_complete = True
        self.write_receipt()
        event("initialization_complete", loaded=len(self.handles), configured=len(self.manifest))

    def _cleanup(self):
        try:
            self.backend.cleanup()
        except Exception as exc:
            event("cleanup_failed", exception_type=type(exc).__name__)

    def _canary(self, name):
        started = time.monotonic()
        try:
            result = self.backend.generate(self.handles[name], "Reply with one word: ok", 1,
                                           self.max_input_tokens, self.generation_max_time_s)
            ok = type(result["output_tokens"]) is int and result["output_tokens"] >= 1
            evidence = {"operational_only": True, "ok": ok, "clock_utc": utc_now(),
                        "output_tokens": result["output_tokens"],
                        "output_sha256": hashlib.sha256(result["generation"].encode()).hexdigest(),
                        "duration_ms": round((time.monotonic() - started) * 1000, 3)}
            with self.state_lock:
                self.states[name].update(canary_ok=ok, canary=evidence,
                                         canary_monotonic=time.monotonic())
            event("canary_complete", model=name, ok=ok,
                  output_tokens=result["output_tokens"], duration_ms=evidence["duration_ms"])
        except Exception as exc:
            with self.state_lock:
                self.states[name].update(canary_ok=False, canary={"operational_only": True,
                    "ok": False, "clock_utc": utc_now(), "error": "canary_failed"},
                    canary_monotonic=time.monotonic())
            event("canary_failed", model=name, exception_type=type(exc).__name__)
            self._cleanup()

    def model_states(self):
        now = time.monotonic()
        with self.state_lock:
            states = {name: dict(state) for name, state in self.states.items()}
        for state in states.values():
            last = state.pop("canary_monotonic", None)
            age = None if last is None else max(0, now - last)
            state["canary_age_seconds"] = None if age is None else round(age, 3)
            state["canary_fresh"] = age is not None and age <= self.canary_max_age_s
            state["canary_ok"] = state["canary_ok"] and state["canary_fresh"]
        return states

    def resources(self):
        disk = vram = None
        try:
            disk = shutil.disk_usage(self.root).free
        except OSError:
            pass
        try:
            if self.backend:
                vram = self.backend.free_vram_mb()
        except Exception:
            pass
        return disk, vram

    def readiness(self):
        disk, vram = self.resources()
        result = readiness_summary(self.manifest, self.model_states(),
            free_disk_bytes=disk, free_vram_mb=vram,
            min_free_disk_bytes=self.min_free_disk_bytes, min_free_vram_mb=self.reserve_mb,
            intentional_exclusions=self.exclusions,
            initialization_complete=self.initialization_complete)
        result.update(schema=SCHEMA, boot_id=self.boot_id, host=self.host_label,
                      clock_utc=utc_now(), evidence="operational_canaries_only")
        return result

    def health(self):
        _, vram = self.resources()
        return {"ok": True, "alive": True, "schema": SCHEMA, "boot_id": self.boot_id,
                "host": self.host_label, "clock_utc": utc_now(),
                "uptime_seconds": round(time.monotonic() - self.started, 3),
                "initialization_complete": self.initialization_complete,
                "loaded": sorted(self.handles), "free_mb": vram}

    def model_catalog(self):
        return {"schema": SCHEMA, "host": self.host_label, "boot_id": self.boot_id,
                "configured_count": len(self.manifest), "manifest": list(self.manifest),
                "intentional_exclusions": self.exclusions, "models": self.model_states()}

    def generate(self, req):
        name, prompt, count = validate_generation_request(req, self.max_prompt_chars, self.max_new_tokens)
        request_id = uuid.uuid4().hex
        if name not in self.states:
            raise ServeError(404, "unknown_model")
        if not self.initialization_complete or name not in self.handles:
            raise ServeError(503, "model_unavailable")
        expected = req.get("expected_artifact_fingerprint")
        if expected is not None and not hmac.compare_digest(expected, self.states[name]["artifact_fingerprint"]):
            raise ServeError(409, "artifact_identity_mismatch")
        with self.state_lock:
            self.stats["requests"] += 1
        try:
            with self.gate.slot(timeout=self.queue_timeout_s):
                try:
                    result = self.backend.generate(self.handles[name], prompt, count,
                                                   self.max_input_tokens, self.generation_max_time_s)
                except ServeError:
                    raise
                except Exception as exc:
                    with self.state_lock:
                        self.states[name]["canary_ok"] = False
                    is_oom = self.backend.is_oom(exc)
                    event("generation_oom" if is_oom else "generation_failed", model=name,
                          request_id=request_id, exception_type=type(exc).__name__)
                    # Keep adapter state and OOM cleanup inside the admission slot.
                    self._cleanup()
                    raise ServeError(503 if is_oom else 500,
                                     "generation_oom" if is_oom else "generation_failed") from None
            with self.state_lock:
                self.stats["succeeded"] += 1
                self.stats["output_tokens"] += result["output_tokens"]
            event("generation_complete", request_id=request_id, model=name,
                  input_tokens=result["input_tokens"], output_tokens=result["output_tokens"],
                  duration_ms=result["duration_ms"])
            return {"model": name, "generation": result["generation"],
                    "request_id": request_id, "boot_id": self.boot_id,
                    "repo": self.states[name]["repo"], "revision": self.states[name]["revision"],
                    "artifact_fingerprint": self.states[name]["artifact_fingerprint"],
                    "completion_tokens": result["output_tokens"],
                    "elapsed_ms": result["duration_ms"],
                    "usage": {"input_tokens": result["input_tokens"],
                              "output_tokens": result["output_tokens"]},
                    "duration_ms": result["duration_ms"]}
        except AdmissionRejected as exc:
            with self.state_lock:
                self.stats["busy"] += 1
            raise ServeError(503, exc.code) from None
        except ServeError:
            with self.state_lock:
                self.stats["failed"] += 1
            raise

    def receipt(self):
        with self.state_lock:
            counters = dict(self.stats)
        ready = self.readiness()
        states = self.model_states()
        gpu = None
        try:
            gpu = self.backend.gpu_name()
        except Exception:
            pass
        return {"schema": SCHEMA, "clock_utc": utc_now(), "boot_utc": self.boot_utc,
                "host": self.host_label, "boot_id": self.boot_id,
                "source_sha256": self.sources, "readiness": ready,
                "manifest": self.manifest, "models": states,
                "loaded": sorted(name for name, state in states.items() if state["status"] == "loaded"),
                "statuses": {name: state["status"] for name, state in states.items()},
                "free_mb": ready["resources"]["vram"]["free_mb"], "gpu": gpu,
                "intentional_exclusions": self.exclusions,
                "admission": self.gate.snapshot(), "counters": counters}

    def write_receipt(self):
        try:
            rec = self.receipt()
            atomic_json(self.receipt_path, rec)
            return rec
        except Exception as exc:
            event("receipt_write_failed", exception_type=type(exc).__name__)
            return None

    def refresh_canaries(self):
        while not self.shutdown_event.wait(60):
            for name in sorted(self.handles):
                with self.state_lock:
                    last = self.states[name].get("canary_monotonic", 0)
                if time.monotonic() - last < self.canary_interval_s:
                    continue
                try:
                    with self.gate.slot(timeout=0):
                        self._canary(name)
                except AdmissionRejected:
                    break
                if self.shutdown_event.is_set():
                    return

    def maintenance(self):
        while not self.shutdown_event.wait(60):
            self.write_receipt()

    def upload_heartbeats(self):
        # Separate thread: an unavailable Hub cannot delay the local receipt.
        while not self.shutdown_event.wait(600):
            try:
                from huggingface_hub import HfApi
                HfApi(token=self.config.get("hf_token")).upload_file(
                    path_or_fileobj=io.BytesIO(json.dumps(self.receipt(), sort_keys=True).encode()),
                    path_in_repo="mass-modelhost/" + self.host_label + "-hb.json",
                    repo_id="SZLHOLDINGS/wave-logs", repo_type="dataset")
            except Exception as exc:
                event("heartbeat_upload_failed", exception_type=type(exc).__name__)


class Handler(BaseHTTPRequestHandler):
    server_version = "SZLModelHost/2"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def setup(self):
        self.request.settimeout(self.server.host.socket_timeout_s)
        super().setup()

    def _json(self, status, value):
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        if status == 503:
            self.send_header("Retry-After", "2")
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass

    def _authorized(self):
        token = self.server.host.origin_auth_token
        if token is None:
            return True
        headers = self.headers.get_all("Authorization", [])
        return len(headers) == 1 and hmac.compare_digest(headers[0].encode(), ("Bearer " + token).encode())

    def do_GET(self):
        host = self.server.host
        if self.path == "/health":
            return self._json(200, host.health())
        if not self._authorized():
            return self._json(401, {"err": "unauthorized"})
        if self.path in ("/ready", "/readyz"):
            report = host.readiness()
            return self._json(report["http_status"], report)
        if self.path == "/models":
            return self._json(200, host.model_catalog())
        self._json(404, {"err": "not_found"})

    def do_POST(self):
        if not self._authorized():
            return self._json(401, {"err": "unauthorized"})
        if self.path != "/generate":
            return self._json(404, {"err": "not_found"})
        if self.headers.get("Transfer-Encoding") is not None:
            return self._json(400, {"err": "unsupported_transfer_encoding"})
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or re.fullmatch(r"[0-9]{1,10}", lengths[0]) is None:
            return self._json(411, {"err": "content_length_required"})
        length = int(lengths[0])
        if length < 1 or length > self.server.host.max_body_bytes:
            return self._json(413, {"err": "body_too_large"})
        if self.headers.get_content_type() != "application/json":
            return self._json(415, {"err": "content_type_must_be_json"})
        try:
            data = self.rfile.read(length)
            if len(data) != length:
                return self._json(400, {"err": "incomplete_body"})
            req = json.loads(data)
            return self._json(200, self.server.host.generate(req))
        except (TimeoutError, socket.timeout):
            return self._json(408, {"err": "request_timeout"})
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
            return self._json(400, {"err": "invalid_json"})
        except ContractError as exc:
            return self._json(413 if exc.code == "prompt_too_large" else 400, {"err": exc.code})
        except ServeError as exc:
            return self._json(exc.status, {"err": exc.code})
        except Exception as exc:
            event("request_failed", exception_type=type(exc).__name__)
            return self._json(500, {"err": "internal_error"})

    def log_message(self, *args):
        pass


class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, address, host):
        self.host = host
        self.worker_slots = threading.BoundedSemaphore(integer_limit(host.config, "max_http_workers", 8))
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.worker_slots.acquire(blocking=False):
            try:
                request.settimeout(0.5)
                body = b'{"err":"http_workers_busy"}'
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json\r\n"
                                b"Connection: close\r\nRetry-After: 2\r\nContent-Length: "
                                + str(len(body)).encode() + b"\r\n\r\n" + body)
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.worker_slots.release()

    def handle_error(self, request, client_address):
        event("http_worker_failed")


def main(argv=None):
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(root / "host_config.json"))
    parser.add_argument("--lock", default=str(root / "model_lock.json"))
    parser.add_argument("--bind")
    parser.add_argument("--port", type=int)
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as stream:
        config = json.load(stream)
    with open(args.lock, encoding="utf-8") as stream:
        lock = json.load(stream)
    host = ModelHost(config, lock, lock_path=args.lock)
    event("boot", host=host.host_label, boot_id=host.boot_id, source_sha256=host.sources)
    # Local-only calls below prevent downloads while allowing optional telemetry upload.
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    host.initialize()
    server = BoundedHTTPServer((args.bind or config.get("bind", "127.0.0.1"),
                                args.port or integer_limit(config, "port", 8090)), host)
    for target, name in ((host.maintenance, "modelhost-maintenance"),
                         (host.refresh_canaries, "modelhost-canaries")):
        threading.Thread(target=target, name=name, daemon=True).start()
    if config.get("heartbeat_upload") is True:
        threading.Thread(target=host.upload_heartbeats, name="modelhost-upload", daemon=True).start()
    event("listening", bind=server.server_address[0], port=server.server_address[1])
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        host.shutdown_event.set()
        server.server_close()
        host.write_receipt()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        event("startup_failed", code=exc.code if isinstance(exc, ContractError) else "startup_error",
              exception_type=type(exc).__name__)
        raise SystemExit(1)
