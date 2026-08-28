# SPDX-License-Identifier: Apache-2.0
import argparse, json, sys
from .recipe import recipe
from .schema import validate_plan
from .energy import measure_or_unavailable

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="szl-serve")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("recipe")
    v = sub.add_parser("validate"); v.add_argument("plan")
    sub.add_parser("energy")
    args = p.parse_args(argv)
    if args.cmd == "recipe":
        print(json.dumps(recipe(), indent=2)); return 0
    if args.cmd == "energy":
        j, lab = measure_or_unavailable()
        print(json.dumps({"measured_joules": j, "label": lab})); return 0
    plan = json.loads(open(args.plan, encoding="utf-8").read())
    ok, msg = validate_plan(plan)
    print(json.dumps({"ok": ok, "detail": msg}))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
