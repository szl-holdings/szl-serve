# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Thin CLI: validate a plan JSON, print the LIVE Space + airgap recipe."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from szl_serve.recipe import format_recipe
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

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        return _cmd_validate(args.plan)
    if args.cmd == "recipe":
        return _cmd_recipe()
    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
