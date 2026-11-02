# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""CLI for proposal validation, recipes, and read-only runtime qualification."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Optional, Sequence

from szl_serve.kernels import probe_estate, selfcheck
from szl_serve.qualify import qualify
from szl_serve.recipe import LIVE_SPACE_BASE, format_recipe
from szl_serve.schema import DISPOSITION_REJECT, validate_plan_file


def _cmd_validate(path: str) -> int:
    result = validate_plan_file(path)
    payload = result.to_dict()
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if not result.ok:
        sys.stderr.write(
            f"REJECT ({len(result.reasons)} reason(s)); plan was NOT repaired.\n"
        )
        return 1
    return 0


def _cmd_recipe() -> int:
    sys.stdout.write(format_recipe())
    return 0


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _cmd_qualify(
    base_url: str,
    output: str,
    timeout_seconds: float,
    max_response_bytes: int,
) -> int:
    payload = qualify(
        base_url,
        timeout_seconds=timeout_seconds,
        max_response_bytes=max_response_bytes,
    )
    if output == "-":
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _write_json_atomic(Path(output), payload)
    return 0 if payload["state"] == "OBSERVED" else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="szl_serve",
        description=(
            "SZL governed-inference serve recipe: pin the MEASURED HF Space, "
            "validate plans outside the weights, print the airgap twin. "
            "Not vLLM. Not a tokens/s leaderboard."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate a plan JSON (fail closed; no repair).")
    p_val.add_argument("plan", help="Path to a Khipu plan JSON fixture or model proposal.")

    sub.add_parser("recipe", help="Print the LIVE Space curl + llama.cpp/Ollama airgap twin.")
    sub.add_parser("kernels", help="Import+call the SZL kernel estate or report UNAVAILABLE.")
    p_qualify = sub.add_parser(
        "qualify",
        help="Read identity/contract surfaces and write a fail-closed qualification receipt.",
    )
    p_qualify.add_argument("--base-url", default=LIVE_SPACE_BASE)
    p_qualify.add_argument("--output", required=True, help="Receipt path, or '-' for stdout.")
    p_qualify.add_argument("--timeout-seconds", type=float, default=5.0)
    p_qualify.add_argument("--max-response-bytes", type=int, default=64 * 1024)

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        return _cmd_validate(args.plan)
    if args.cmd == "recipe":
        return _cmd_recipe()
    if args.cmd == "kernels":
        payload = {"selfcheck": selfcheck(), "estate": probe_estate()}
        json.dump(payload, sys.stdout, indent=2, sort_keys=True, default=str)
        sys.stdout.write("\n")
        return 0 if payload["selfcheck"].get("ok") else 1
    if args.cmd == "qualify":
        return _cmd_qualify(
            args.base_url,
            args.output,
            args.timeout_seconds,
            args.max_response_bytes,
        )
    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
