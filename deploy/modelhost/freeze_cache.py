#!/usr/bin/env python3
"""Freeze an existing Hugging Face cache into a byte-verified serving lock.

This command never contacts the Hub or downloads weights. It does not modify
cache files. Missing entries remain visible in the configured denominator.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

from contract import ContractError, choose_adapter_config


MAX_SAFETENSORS_HEADER_BYTES = 16 * 1024 * 1024
_FLOAT_WIDTHS = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2,
                 "F8_E4M3": 1, "F8_E5M2": 1, "F8_E8M0": 1}
_INTEGER_WIDTHS = {"BOOL": 1, "I8": 1, "U8": 1, "I16": 2, "U16": 2,
                   "I32": 4, "U32": 4, "I64": 8, "U64": 8}


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_safetensors_key", "Safetensors JSON contains duplicate keys")
        result[key] = value
    return result


def project_safetensors_bf16(path):
    """Read only a bounded header and project tensors to the loader's BF16 dtype.

    Floating tensors use two destination bytes per element. Integer and Boolean
    buffers retain their stored width. Validate exact sizes, contiguous spans,
    and file bounds without reading tensor data or importing a tensor library.
    """
    path = Path(path)
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ContractError("truncated_safetensors_header", "Safetensors length prefix is missing")
        header_bytes = int.from_bytes(prefix, "little", signed=False)
        if header_bytes < 2 or header_bytes > MAX_SAFETENSORS_HEADER_BYTES:
            raise ContractError("invalid_safetensors_header_size", "Safetensors header exceeds its bounds")
        if 8 + header_bytes > before.st_size:
            raise ContractError("truncated_safetensors_header", "Safetensors header is truncated")
        raw = stream.read(header_bytes)
        if len(raw) != header_bytes or not raw.startswith(b"{"):
            raise ContractError("invalid_safetensors_header", "Safetensors header is invalid")
        try:
            header = json.loads(raw, object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as error:
            raise ContractError("invalid_safetensors_header", "Safetensors header is not valid JSON") from error
        if not isinstance(header, dict):
            raise ContractError("invalid_safetensors_header", "Safetensors header must be an object")
        data_bytes = before.st_size - 8 - header_bytes
        spans = []
        dtype_elements = {}
        tensor_count = projected_bytes = stored_bytes = 0
        for name, tensor in header.items():
            if name == "__metadata__":
                if not isinstance(tensor, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                       for k, v in tensor.items()):
                    raise ContractError("invalid_safetensors_metadata", "Metadata must map strings to strings")
                continue
            if not isinstance(tensor, dict):
                raise ContractError("invalid_safetensors_tensor", "Tensor metadata must be an object")
            dtype = tensor.get("dtype")
            if not isinstance(dtype, str) or dtype not in _FLOAT_WIDTHS.keys() | _INTEGER_WIDTHS.keys():
                raise ContractError("unsupported_safetensors_dtype", "Unsupported safetensors dtype")
            shape = tensor.get("shape")
            if (not isinstance(shape, list) or len(shape) > 64
                    or any(type(dim) is not int or dim < 0 or dim > 2 ** 63 - 1 for dim in shape)):
                raise ContractError("invalid_safetensors_shape", "Tensor shape must contain nonnegative integer dimensions")
            elements = 1
            for dim in shape:
                elements *= dim
            width = _FLOAT_WIDTHS.get(dtype, _INTEGER_WIDTHS.get(dtype))
            size = elements * width
            offsets = tensor.get("data_offsets")
            if (not isinstance(offsets, list) or len(offsets) != 2
                    or any(type(offset) is not int for offset in offsets)
                    or not 0 <= offsets[0] <= offsets[1] <= data_bytes
                    or offsets[1] - offsets[0] != size):
                raise ContractError("invalid_safetensors_offsets", "Tensor span differs from its shape or file bounds")
            spans.append(tuple(offsets))
            tensor_count += 1
            stored_bytes += size
            projected_bytes += elements * (2 if dtype in _FLOAT_WIDTHS else width)
            dtype_elements[dtype] = dtype_elements.get(dtype, 0) + elements
        cursor = 0
        for start, end in sorted(spans):
            if start != cursor:
                raise ContractError("invalid_safetensors_layout", "Tensor spans must be contiguous and nonoverlapping")
            cursor = end
        if cursor != data_bytes or tensor_count == 0:
            raise ContractError("invalid_safetensors_layout", "Tensor spans must cover the entire data buffer")
        after = os.fstat(stream.fileno())
    current = path.stat()
    signature = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if signature(before) != signature(after) or signature(before) != signature(current):
        raise ContractError("artifact_changed", "Safetensors file changed while reading its header")
    return {"file_bytes": before.st_size, "header_bytes": header_bytes,
            "tensor_count": tensor_count, "stored_tensor_bytes": stored_bytes,
            "projected_bf16_bytes": projected_bytes,
            "dtype_elements": dict(sorted(dtype_elements.items()))}


def estimate_base_vram(base_path, files):
    """Return advisory allocation planning; these fields do not enter identity."""
    weights = sorted(item["path"] for item in files if item["path"].endswith(".safetensors"))
    if not weights:
        raise ContractError("missing_base_weights", "No safetensors base weights are available")
    reports = {name: project_safetensors_bf16(Path(base_path) / name) for name in weights}
    projected = sum(report["projected_bf16_bytes"] for report in reports.values())
    # Preserve the existing five-percent headroom, 256 MiB fixed overhead,
    # and 900 MiB floor. Only the projected tensor allocation changes.
    denominator = 100 * 1024 ** 2
    estimated = max(900, (projected * 105 + denominator - 1) // denominator + 256)
    return {"estimated_vram_mb": estimated,
            "vram_planning": {"method": "safetensors_bf16_projection/v1",
                              "target_float_dtype": "BF16", "headroom_percent": 5,
                              "fixed_overhead_mb": 256, "minimum_mb": 900,
                              "stored_tensor_bytes": sum(report["stored_tensor_bytes"] for report in reports.values()),
                              "projected_bf16_bytes": projected, "weight_files": reports}}


def fingerprint(spec, base):
    identity = {"repo": spec["repo"], "revision": spec["revision"],
                "adapter_config": spec["adapter_config"], "files": spec["files"],
                "base": {"repo": base["repo"], "revision": base["revision"],
                         "files": base["files"]}}
    return hashlib.sha256(json.dumps(identity, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def hash_file(path):
    before = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ContractError("artifact_changed", "A cache file changed while hashing")
    return {"size": after.st_size, "sha256": h.hexdigest()}


def snapshot(cache, repo):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ContractError("invalid_repository", "Invalid repository identifier")
    root = cache / ("models--" + repo.replace("/", "--"))
    ref = root / "refs" / "main"
    if not ref.is_file():
        raise ContractError("missing_cached_revision", "No cached main revision")
    revision = ref.read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ContractError("invalid_cached_revision", "Expected immutable 40-character revision")
    path = root / "snapshots" / revision
    if not path.is_dir():
        raise ContractError("missing_cached_snapshot", "Cached snapshot is missing")
    return revision, path


def inventory(root, paths):
    output = []
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file():
            raise ContractError("missing_cached_file", "A required cached file is missing")
        output.append({"path": relative, **hash_file(path)})
    return output


def base_inventory(path):
    names = [p.name for p in path.iterdir() if p.is_file()]
    weights = [name for name in names if name.endswith(".safetensors")]
    if not weights or "config.json" not in names:
        raise ContractError("missing_base_weights", "Complete safetensors base is not cached")
    index = path / "model.safetensors.index.json"
    if index.exists():
        expected = set(json.loads(index.read_text())["weight_map"].values())
        if not expected <= set(weights):
            raise ContractError("missing_base_shard", "A base model shard is not cached")
    # Pin every cached root file: includes the tokenizer and generation config.
    # Never use trust_remote_code; arbitrary repository Python is not executed.
    return inventory(path, names)


def freeze(config, cache, exclusions=()):
    manifest = config["manifest"]
    if len({repo.split("/")[-1] for repo in manifest}) != len(manifest):
        raise ContractError("duplicate_model_name", "Manifest aliases must be unique")
    exclusion_reasons = (dict(exclusions) if isinstance(exclusions, dict) else
                         {name: "protected_workload_vram_capacity" for name in exclusions})
    if any(not isinstance(reason, str) or not reason for reason in exclusion_reasons.values()):
        raise ContractError("invalid_exclusion_reason", "Each exclusion needs an explicit reason")
    excluded = set(exclusion_reasons)
    if not excluded <= {repo.split("/")[-1] for repo in manifest}:
        raise ContractError("unknown_exclusion", "Excluded model is absent from manifest")
    output = {"schema": "szl.modelhost-lock/v2",
              "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "host_label": config["host_label"], "manifest": manifest,
              "intentional_exclusions": dict(sorted(exclusion_reasons.items())),
              "bases": {}, "models": {}}
    failed_bases = {}
    for repo in manifest:
        name = repo.split("/")[-1]
        spec = {"name": name, "repo": repo, "status": "unavailable"}
        output["models"][name] = spec
        try:
            revision, root = snapshot(cache, repo)
            configs = [p.relative_to(root).as_posix()
                       for p in root.rglob("adapter_config.json") if p.is_file()]
            pick = choose_adapter_config(configs)
            adir = root / PurePosixPath(pick).parent
            adapter = json.loads((root / pick).read_text())
            base_repo = adapter["base_model_name_or_path"]
            # Safetensors is the only accepted adapter format in this deployment.
            # Avoid introducing pickle deserialization during a hardening rollout.
            weights = [p.name for p in adir.iterdir()
                       if p.is_file() and p.name in ("adapter_model.safetensors", "adapter.safetensors")]
            if len(weights) != 1:
                raise ContractError("ambiguous_adapter_weights", "Expected one safetensors adapter")
            spec.update(revision=revision, kind="lora", adapter_config=pick,
                        path=str(adir), files=inventory(adir, ["adapter_config.json"] + weights))
            if name in excluded:
                spec["reason"] = exclusion_reasons[name]
                continue
            base_revision, base_path = snapshot(cache, base_repo)
            base_key = hashlib.sha256((base_repo + "@" + base_revision).encode()).hexdigest()[:24]
            if base_key in failed_bases:
                raise ContractError(failed_bases[base_key], "Base is unavailable")
            if base_key not in output["bases"]:
                try:
                    files = base_inventory(base_path)
                    planning = estimate_base_vram(base_path, files)
                    output["bases"][base_key] = {
                        "repo": base_repo, "revision": base_revision,
                        "path": str(base_path), "files": files,
                        **planning,
                    }
                except ContractError as error:
                    failed_bases[base_key] = error.code
                    raise
            spec.update(base_key=base_key, status="pinned")
            spec["artifact_fingerprint"] = fingerprint(spec, output["bases"][base_key])
        except ContractError as error:
            spec["reason"] = error.code
        except (OSError, ValueError, KeyError) as error:
            spec["reason"] = "invalid_cached_artifact"
            spec["error_type"] = type(error).__name__
        print(json.dumps({"model": name, "status": spec["status"],
                          "reason": spec.get("reason"), "revision": spec.get("revision"),
                          "adapter_config": spec.get("adapter_config")}), flush=True)
    return output


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".lock-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--exclusion-policy", type=Path,
                        help="JSON object mapping configured model names to reviewed exclusion reasons")
    args = parser.parse_args()
    exclusions = {name: "protected_workload_vram_capacity" for name in args.exclude}
    if args.exclusion_policy:
        exclusions.update(json.loads(args.exclusion_policy.read_text()))
    result = freeze(json.loads(args.config.read_text()), args.cache, exclusions)
    atomic_json(args.output, result)
    print(json.dumps({"output": str(args.output), "configured": len(result["manifest"]),
                      "pinned": sum(x["status"] == "pinned" for x in result["models"].values()),
                      "exclusions": len(result["intentional_exclusions"]),
                      "bases": len(result["bases"])}), flush=True)


if __name__ == "__main__":
    main()
