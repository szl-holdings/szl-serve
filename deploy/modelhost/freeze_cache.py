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
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

from contract import ContractError, choose_adapter_config


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
                    weight_bytes = sum(item["size"] for item in files
                                       if item["path"].endswith(".safetensors"))
                    output["bases"][base_key] = {
                        "repo": base_repo, "revision": base_revision,
                        "path": str(base_path), "files": files,
                        "estimated_vram_mb": max(900, math.ceil(weight_bytes / 1024**2 * 1.05) + 256),
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
