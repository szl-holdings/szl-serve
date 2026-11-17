import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from deduplicate_cache import consolidate
from contract import ContractError
from freeze_cache import (MAX_SAFETENSORS_HEADER_BYTES, estimate_base_vram, freeze,
                          project_safetensors_bf16)


def safetensors_bytes(tensors=None, data=None):
    tensors = tensors or {"weight": {"dtype": "BF16", "shape": [2], "data_offsets": [0, 4]}}
    header = json.dumps(tensors, separators=(",", ":")).encode()
    header += b" " * (-len(header) % 8)
    if data is None:
        size = max(value["data_offsets"][1] for name, value in tensors.items() if name != "__metadata__")
        data = b"\x00" * size
    return len(header).to_bytes(8, "little") + header + data


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
        base_weights = safetensors_bytes()
        old_weights = safetensors_bytes(data=b"\x01" * 4)
        final_weights = safetensors_bytes(data=b"\x02" * 4)
        self.snapshot("org/base", {"config.json": b"{}", "model.safetensors": base_weights, "tokenizer.json": b"{}"})
        self.snapshot("org/model", {"checkpoint-10/adapter_config.json": adapter,
                                   "checkpoint-10/adapter_model.safetensors": old_weights,
                                   "final/adapter_config.json": adapter,
                                   "final/adapter_model.safetensors": final_weights})
        with contextlib.redirect_stdout(io.StringIO()):
            result = freeze({"host_label": "fixture", "manifest": ["org/model", "org/missing"]}, self.root)
        model = result["models"]["model"]
        self.assertEqual(model["adapter_config"], "final/adapter_config.json")
        self.assertTrue(model["path"].endswith("/final"))
        self.assertEqual(model["status"], "pinned")
        self.assertEqual(len(result["manifest"]), 2)
        self.assertEqual(result["models"]["missing"]["reason"], "missing_cached_revision")
        self.assertEqual([f["sha256"] for f in model["files"] if f["path"].endswith(".safetensors")],
                         [hashlib.sha256(final_weights).hexdigest()])
        base = result["bases"][model["base_key"]]
        self.assertEqual(base["estimated_vram_mb"], 900)
        self.assertEqual(base["vram_planning"]["projected_bf16_bytes"], 4)

    def test_freeze_rejects_missing_shard(self):
        adapter = json.dumps({"base_model_name_or_path": "org/base"}).encode()
        self.snapshot("org/base", {"config.json": b"{}", "model-1.safetensors": safetensors_bytes(),
                      "model.safetensors.index.json": b'{"weight_map":{"a":"model-1.safetensors","b":"model-2.safetensors"}}'})
        self.snapshot("org/model", {"adapter_config.json": adapter, "adapter_model.safetensors": safetensors_bytes()})
        with contextlib.redirect_stdout(io.StringIO()):
            result = freeze({"host_label": "fixture", "manifest": ["org/model"]}, self.root)
        self.assertEqual(result["models"]["model"]["status"], "unavailable")
        self.assertEqual(result["models"]["model"]["reason"], "missing_base_shard")


class SafetensorsProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "model.safetensors"

    def tearDown(self):
        self.temp.cleanup()

    def project(self, tensors=None, data=None):
        self.path.write_bytes(safetensors_bytes(tensors, data))
        return project_safetensors_bf16(self.path)

    def test_float32_projects_to_bfloat16(self):
        result = self.project({"weight": {"dtype": "F32", "shape": [2, 3], "data_offsets": [0, 24]}})
        self.assertEqual(result["stored_tensor_bytes"], 24)
        self.assertEqual(result["projected_bf16_bytes"], 12)
        self.assertEqual(result["dtype_elements"], {"F32": 6})

    def test_bfloat16_preserves_tensor_bytes(self):
        result = self.project()
        self.assertEqual(result["stored_tensor_bytes"], 4)
        self.assertEqual(result["projected_bf16_bytes"], 4)

    def test_integer_and_boolean_buffers_keep_width(self):
        result = self.project({"weight": {"dtype": "F32", "shape": [2], "data_offsets": [0, 8]},
                               "positions": {"dtype": "I64", "shape": [2], "data_offsets": [8, 24]},
                               "mask": {"dtype": "BOOL", "shape": [3], "data_offsets": [24, 27]}})
        self.assertEqual(result["stored_tensor_bytes"], 27)
        self.assertEqual(result["projected_bf16_bytes"], 23)

    def test_oversized_header_rejected_before_reading_body(self):
        self.path.write_bytes((MAX_SAFETENSORS_HEADER_BYTES + 1).to_bytes(8, "little"))
        with self.assertRaises(ContractError) as error:
            project_safetensors_bf16(self.path)
        self.assertEqual(error.exception.code, "invalid_safetensors_header_size")

    def test_truncated_header_rejected(self):
        for raw in (b"short", (100).to_bytes(8, "little") + b"{}"):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ContractError) as error:
                project_safetensors_bf16(self.path)
            self.assertEqual(error.exception.code, "truncated_safetensors_header")

    def test_malformed_offsets_and_truncated_data_rejected(self):
        cases = [([0, 3], b"\x00" * 4), ([0, 4], b"\x00" * 2),
                 ([1, 5], b"\x00" * 4), ([True, 4], b"\x00" * 4),
                 ([-1, 3], b"\x00" * 4), ([0, 4, 4], b"\x00" * 4)]
        for offsets, data in cases:
            with self.subTest(offsets=offsets, data_size=len(data)), self.assertRaises(ContractError) as error:
                self.project({"weight": {"dtype": "BF16", "shape": [2], "data_offsets": offsets}}, data)
            self.assertEqual(error.exception.code, "invalid_safetensors_offsets")

    def test_overlaps_gaps_and_extra_data_rejected(self):
        cases = [({"a": {"dtype": "BF16", "shape": [2], "data_offsets": [0, 4]},
                   "b": {"dtype": "BF16", "shape": [2], "data_offsets": [2, 6]}}, 6),
                 ({"a": {"dtype": "BF16", "shape": [2], "data_offsets": [1, 5]}}, 5),
                 ({"a": {"dtype": "BF16", "shape": [2], "data_offsets": [0, 4]}}, 5)]
        for tensors, size in cases:
            with self.subTest(size=size), self.assertRaises(ContractError) as error:
                self.project(tensors, b"\x00" * size)
            self.assertEqual(error.exception.code, "invalid_safetensors_layout")

    def test_invalid_shapes_and_unknown_dtype_rejected(self):
        for shape in ([True], [-1], [2.0], "2"):
            with self.subTest(shape=shape), self.assertRaises(ContractError) as error:
                self.project({"weight": {"dtype": "BF16", "shape": shape, "data_offsets": [0, 4]}}, b"\x00" * 4)
            self.assertEqual(error.exception.code, "invalid_safetensors_shape")
        with self.assertRaises(ContractError) as error:
            self.project({"weight": {"dtype": "UNKNOWN", "shape": [2], "data_offsets": [0, 4]}}, b"\x00" * 4)
        self.assertEqual(error.exception.code, "unsupported_safetensors_dtype")

    def test_scalar_empty_tensor_and_metadata_supported(self):
        result = self.project({"__metadata__": {"format": "pt"},
                               "empty": {"dtype": "BF16", "shape": [0], "data_offsets": [0, 0]},
                               "scalar": {"dtype": "F32", "shape": [], "data_offsets": [0, 4]}})
        self.assertEqual(result["tensor_count"], 2)
        self.assertEqual(result["projected_bf16_bytes"], 2)

    def test_projection_preserves_existing_headroom_and_reads_no_tensor_payload(self):
        # A sparse file represents 2 GiB of F32 storage without allocating or
        # reading tensor data. Its BF16 allocation is 1 GiB plus unchanged policy.
        elements = 512 * 1024 ** 2
        header = json.dumps({"weight": {"dtype": "F32", "shape": [elements],
                                         "data_offsets": [0, elements * 4]}}).encode()
        with self.path.open("wb") as stream:
            stream.write(len(header).to_bytes(8, "little") + header)
            stream.truncate(8 + len(header) + elements * 4)
        result = estimate_base_vram(self.path.parent, [{"path": self.path.name}])
        self.assertEqual(result["estimated_vram_mb"], 1332)
        self.assertEqual(result["vram_planning"]["projected_bf16_bytes"], 1024 ** 3)
        self.assertEqual(result["vram_planning"]["headroom_percent"], 5)
        self.assertEqual(result["vram_planning"]["fixed_overhead_mb"], 256)


if __name__ == "__main__":
    unittest.main()
