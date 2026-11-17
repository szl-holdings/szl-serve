import copy
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest

from qualify_running import atomic_report, qualify


class FakeClient:
    def __init__(self, catalog, disk_ready=True):
        self.catalog = catalog
        self.disk_ready = disk_ready
        self.calls = []
        self.generations = []
        self.final_boot = "test-boot"
        self.ready_reads = 0
        self.bad_negative = False

    def request(self, method, path, payload=None, raw_body=None):
        self.calls.append((method, path))
        if path == "/health":
            return 200, {"schema": "szl.modelhost/v2", "boot_id": "test-boot", "alive": True,
                         "initialization_complete": True}
        if path == "/models":
            return 200, self.catalog
        if path == "/ready":
            self.ready_reads += 1
            return (200 if self.disk_ready else 503), {
                "schema": "szl.modelhost/v2", "boot_id": "test-boot" if self.ready_reads == 1 else self.final_boot,
                "ready": self.disk_ready, "configured_count": 4, "required_count": 3,
                "intentional_exclusions": ["metadata"],
                "reasons": [] if self.disk_ready else ["disk_below_reserve"],
                "resources": {"disk": {"free_bytes": 17 * 1024 ** 3, "minimum_bytes": 50 * 1024 ** 3}}}
        if raw_body is not None:
            return 413, {"err": "body_too_large"}
        name = payload["model"]
        if name not in self.catalog["models"]:
            return 404, {"err": "unknown_model"}
        count = payload["max_new_tokens"]
        if type(count) is not int or count > 256:
            return 400, {"err": "invalid_max_new_tokens"}
        row = self.catalog["models"][name]
        if payload.get("expected_artifact_fingerprint") not in (None, row["artifact_fingerprint"]):
            return 409, {"err": "artifact_identity_mismatch"}
        if len(payload["prompt"]) > 5000:
            return (400 if self.bad_negative else 413), {"err": "input_tokens_exceeded"}
        self.generations.append(payload)
        return 200, {"model": name, "repo": row["repo"], "revision": row["revision"],
                     "artifact_fingerprint": row["artifact_fingerprint"], "boot_id": "test-boot",
                     "completion_tokens": 8, "elapsed_ms": 12.25,
                     "generation": "PRIVATE_OUTPUT_MUST_NOT_BE_RETAINED"}


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "szl_modelhost.py").write_bytes(b"server")
        (self.root / "contract.py").write_bytes(b"contract")
        self.server_sha = hashlib.sha256(b"server").hexdigest()
        self.contract_sha = hashlib.sha256(b"contract").hexdigest()
        self.config = {"host_label": "test", "manifest": ["org/a", "org/b", "org/c", "org/metadata"]}
        (self.root / "receipts").mkdir()
        (self.root / "receipts" / "latest.json").write_text(json.dumps({
            "schema": "szl.modelhost/v2", "boot_id": "test-boot", "source_sha256": {
                "szl_modelhost.py": self.server_sha, "contract.py": self.contract_sha}}))
        models = {}
        for name in ("a", "b", "c"):
            models[name] = {"repo": "org/" + name, "revision": "d" * 40, "status": "loaded",
                            "identity_verified": True, "canary_ok": True, "canary_fresh": True,
                            "artifact_fingerprint": hashlib.sha256(name.encode()).hexdigest(),
                            "base": "org/shared" if name != "c" else "org/second", "base_revision": "e" * 40}
        models["metadata"] = {"status": "excluded", "repo": "org/metadata"}
        self.catalog = {"schema": "szl.modelhost/v2", "boot_id": "test-boot", "configured_count": 4,
                        "manifest": self.config["manifest"], "intentional_exclusions": {"metadata": "no_weights"},
                        "models": models}

    def tearDown(self):
        self.temp.cleanup()

    def run_qualification(self, client=None, source_sha=None):
        client = client or FakeClient(self.catalog)
        return qualify(self.config, self.root, source_sha or self.server_sha, self.contract_sha,
                       client, expected_configured_count=4), client

    def test_one_generation_per_base_and_content_never_retained(self):
        report, client = self.run_qualification()
        self.assertTrue(report["operational_pass"])
        self.assertTrue(report["fully_ready"])
        self.assertEqual(len(client.generations), 2)
        self.assertEqual({p["model"] for p in client.generations}, {"a", "c"})
        self.assertTrue(all(p["max_new_tokens"] == 8 for p in client.generations))
        encoded = json.dumps(report)
        self.assertNotIn("PRIVATE_OUTPUT_MUST_NOT_BE_RETAINED", encoded)
        self.assertNotIn("Reply with one short sentence", encoded)
        self.assertTrue(all(row["completion_tokens"] == 8 for row in report["representative_generations"]))

    def test_disk_pressure_is_not_promoted_to_readiness(self):
        report, _ = self.run_qualification(FakeClient(self.catalog, disk_ready=False))
        self.assertTrue(report["operational_pass"])
        self.assertFalse(report["readiness_pass"])
        self.assertFalse(report["fully_ready"])
        self.assertEqual(report["readiness"]["http_status"], 503)
        self.assertEqual(report["readiness"]["body"]["reasons"], ["disk_below_reserve"])

    def test_source_mismatch_prevents_generation(self):
        report, client = self.run_qualification(source_sha="0" * 64)
        self.assertFalse(report["operational_pass"])
        self.assertEqual(client.generations, [])
        self.assertFalse(any(method == "POST" for method, _ in client.calls))

    def test_stale_running_receipt_prevents_generation(self):
        receipt = self.root / "receipts" / "latest.json"
        data = json.loads(receipt.read_text())
        data["boot_id"] = "old-boot"
        receipt.write_text(json.dumps(data))
        report, client = self.run_qualification()
        self.assertFalse(report["operational_pass"])
        self.assertEqual(client.generations, [])

    def test_stale_required_canary_prevents_qualification(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["models"]["b"]["canary_fresh"] = False
        report, client = self.run_qualification(FakeClient(catalog))
        self.assertFalse(report["operational_pass"])
        self.assertEqual(client.generations, [])

    def test_server_restart_during_qualification_fails(self):
        client = FakeClient(self.catalog)
        client.final_boot = "replacement-boot"
        report, _ = self.run_qualification(client)
        self.assertFalse(report["operational_pass"])
        self.assertFalse(report["fully_ready"])

    def test_wrong_negative_status_fails_operational_gate(self):
        client = FakeClient(self.catalog)
        client.bad_negative = True
        report, _ = self.run_qualification(client)
        self.assertFalse(report["operational_pass"])
        failed = [row["name"] for row in report["checks"] if not row["passed"]]
        self.assertEqual(failed, ["excess_input_tokens_rejected"])

    def test_report_is_atomic_private_json(self):
        report, _ = self.run_qualification()
        output = self.root / "output" / "acceptance.json"
        atomic_report(output, report)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(json.loads(output.read_text()), report)
        self.assertEqual([p.name for p in output.parent.iterdir()], ["acceptance.json"])


if __name__ == "__main__":
    unittest.main()
