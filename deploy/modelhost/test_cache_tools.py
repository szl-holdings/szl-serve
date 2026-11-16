import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from deduplicate_cache import consolidate
from freeze_cache import freeze


class CacheToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def pair(self, other=b"same bytes"):
        a, b = self.root / "a", self.root / "b"
        a.write_bytes(b"same bytes")
        b.write_bytes(other)
        a.chmod(0o444)
        b.chmod(0o444)
        return {"source": str(a), "duplicate": str(b), "size": 10,
                "sha256": hashlib.sha256(b"same bytes").hexdigest()}

    def test_audit_does_not_modify_and_apply_is_idempotent(self):
        item = self.pair()
        before = (self.root / "b").stat().st_ino
        self.assertEqual(consolidate(item)["status"], "verified")
        self.assertEqual((self.root / "b").stat().st_ino, before)
        self.assertEqual(consolidate(item, True)["status"], "linked")
        self.assertEqual((self.root / "a").stat().st_ino, (self.root / "b").stat().st_ino)
        self.assertEqual(consolidate(item, True)["status"], "already_linked")

    def test_same_size_different_content_is_never_replaced(self):
        item = self.pair(b"evil bytes")
        with self.assertRaisesRegex(ValueError, "digest_mismatch"):
            consolidate(item, True)
        self.assertEqual((self.root / "b").read_bytes(), b"evil bytes")

    def test_writable_file_is_rejected(self):
        item = self.pair()
        (self.root / "b").chmod(0o644)
        with self.assertRaisesRegex(ValueError, "immutable_regular"):
            consolidate(item, True)

    def test_symlink_is_rejected(self):
        item = self.pair()
        (self.root / "link").symlink_to(self.root / "b")
        item["duplicate"] = str(self.root / "link")
        with self.assertRaisesRegex(ValueError, "symlink_path"):
            consolidate(item, True)

    def snapshot(self, repo, files):
        root = self.root / ("models--" + repo.replace("/", "--"))
        revision = "a" * 40
        (root / "refs").mkdir(parents=True)
        (root / "refs" / "main").write_text(revision)
        snap = root / "snapshots" / revision
        for name, data in files.items():
            target = snap / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return snap

    def test_freeze_selects_exact_final_and_keeps_missing_model(self):
        adapter = json.dumps({"base_model_name_or_path": "org/base"}).encode()
        self.snapshot("org/base", {"config.json": b"{}", "model.safetensors": b"base", "tokenizer.json": b"{}"})
        self.snapshot("org/model", {"checkpoint-10/adapter_config.json": adapter,
                                   "checkpoint-10/adapter_model.safetensors": b"old",
                                   "final/adapter_config.json": adapter,
                                   "final/adapter_model.safetensors": b"final"})
        with contextlib.redirect_stdout(io.StringIO()):
            result = freeze({"host_label": "fixture", "manifest": ["org/model", "org/missing"]}, self.root)
        model = result["models"]["model"]
        self.assertEqual(model["adapter_config"], "final/adapter_config.json")
        self.assertTrue(model["path"].endswith("/final"))
        self.assertEqual(model["status"], "pinned")
        self.assertEqual(len(result["manifest"]), 2)
        self.assertEqual(result["models"]["missing"]["reason"], "missing_cached_revision")
        self.assertEqual([f["sha256"] for f in model["files"] if f["path"].endswith(".safetensors")],
                         [hashlib.sha256(b"final").hexdigest()])

    def test_freeze_rejects_missing_shard(self):
        adapter = json.dumps({"base_model_name_or_path": "org/base"}).encode()
        self.snapshot("org/base", {"config.json": b"{}", "model-1.safetensors": b"base",
                      "model.safetensors.index.json": b'{"weight_map":{"a":"model-1.safetensors","b":"model-2.safetensors"}}'})
        self.snapshot("org/model", {"adapter_config.json": adapter, "adapter_model.safetensors": b"adapter"})
        with contextlib.redirect_stdout(io.StringIO()):
            result = freeze({"host_label": "fixture", "manifest": ["org/model"]}, self.root)
        self.assertEqual(result["models"]["model"]["status"], "unavailable")
        self.assertEqual(result["models"]["model"]["reason"], "missing_base_shard")


if __name__ == "__main__":
    unittest.main()
