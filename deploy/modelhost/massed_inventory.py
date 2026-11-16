#!/usr/bin/env python3
"""Read the authorized Massed fleet with one key and secret-free output."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://vm.massedcompute.com/api/v1/instance"
USER_AGENT = "SZL-Modelhost-Operations/2.0 (authorized fleet audit)"
LIMIT = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def project_instance(row):
    # The provider returns passwords and startup commands alongside metadata.
    # Project only these known fields; never serialize the raw response.
    result = {key: row[key] for key in ("uuid", "name", "ip", "status", "active", "os_booted", "created")
              if key in row and isinstance(row[key], (str, int, float, bool, type(None)))}
    region = row.get("region")
    if isinstance(region, dict) and isinstance(region.get("name"), str):
        result["region"] = region["name"]
    product = row.get("product")
    if isinstance(product, dict) and isinstance(product.get("name"), str):
        result["product"] = product["name"]
    return result


def inventory(key_file):
    key = Path(key_file).read_text(encoding="utf-8").strip()
    if not key or "\n" in key or "\r" in key:
        raise ValueError("invalid_key_file")
    request = urllib.request.Request(ENDPOINT, method="GET", headers={
        "Authorization": "Bearer " + key, "Accept": "application/json", "User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=20) as response:
        raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("response_limit_exceeded")
        status = response.status
    payload = json.loads(raw)
    rows = payload.get("runningInstances") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("unexpected_provider_schema")
    return {"schema": "szl.massed-inventory/v1", "clock_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "http_status": status, "count": len(rows), "instances": [project_instance(row) for row in rows]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path, default=Path(r"C:\SZL\massed_api.key"))
    args = parser.parse_args(argv)
    try:
        result = inventory(args.key_file)
    except urllib.error.HTTPError as exc:
        result = {"schema": "szl.massed-inventory/v1", "http_status": exc.code,
                  "error": "provider_http_error"}
    except Exception as exc:
        result = {"schema": "szl.massed-inventory/v1", "error": "inventory_failed",
                  "exception_type": type(exc).__name__}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
