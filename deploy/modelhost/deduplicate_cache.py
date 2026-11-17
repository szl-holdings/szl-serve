#!/usr/bin/env python3
"""Atomically consolidate explicitly listed, immutable, identical cache blobs.

Default is a read-only audit. --apply replaces only the duplicate directory
entry with a hardlink after both actual SHA-256 hashes and stable metadata
match the reviewed plan. No filename is treated as a content digest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid


def metadata(path):
    p = Path(path)
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError("absolute_normalized_path_required")
    if p.resolve() != p:
        raise ValueError("symlink_path_rejected")
    s = p.stat()
    if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o222:
        raise ValueError("immutable_regular_file_required")
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
            s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode))


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def consolidate(item, apply=False):
    source, target = Path(item["source"]), Path(item["duplicate"])
    first, second = metadata(source), metadata(target)
    change_times = (source.stat().st_ctime_ns, target.stat().st_ctime_ns)
    if first[0] != second[0] or first[2:] != second[2:]:
        # mtime may legitimately differ across downloads; all other attributes
        # still have to agree before the content comparison below.
        if (first[0], first[2], first[4:]) != (second[0], second[2], second[4:]):
            raise ValueError("incompatible_files")
    if first[2] != item["size"]:
        raise ValueError("unexpected_size")
    if digest(source) != item["sha256"] or digest(target) != item["sha256"]:
        raise ValueError("content_digest_mismatch")
    if metadata(source) != first or metadata(target) != second:
        raise ValueError("file_changed_during_audit")
    if change_times != (source.stat().st_ctime_ns, target.stat().st_ctime_ns):
        raise ValueError("file_changed_during_audit")
    result = {"source": str(source), "duplicate": str(target),
              "sha256": item["sha256"], "size": item["size"],
              "source_inode_before": first[1], "duplicate_inode_before": second[1],
              "status": "verified"}
    if first[:2] == second[:2]:
        result["status"] = "already_linked"
        return result
    if not apply:
        return result
    temporary = target.with_name(target.name + ".dedup-" + uuid.uuid4().hex)
    try:
        os.link(source, temporary, follow_symlinks=False)
        if metadata(temporary) != first or metadata(source) != first or metadata(target) != second:
            raise ValueError("file_changed_before_replace")
        os.replace(temporary, target)
        fd = os.open(str(target.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        now = metadata(target)
        if now[:2] != first[:2] or now[2:] != first[2:]:
            raise RuntimeError("hardlink_verification_failed")
        result["status"] = "linked"
        result["inode_after"] = now[1]
        return result
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    for entry in plan:
        print(json.dumps(consolidate(entry, args.apply)), flush=True)


if __name__ == "__main__":
    main()
