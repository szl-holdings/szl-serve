#!/usr/bin/env python3
"""Single-pass operational qualification of an already-running loopback host.

Does not restart services, load models, alter configuration, or install packages.
Real generation is limited to eight tokens on one model per loaded base. Reports
contain output hashes and measured token counts, never prompt or output text.
An operational pass does not imply readiness, quality, or a signed attestation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import http.client
from importlib import metadata
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
SERVER_SCHEMA = "szl.modelhost/v2"


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("file_limit")
    return json.loads(raw)


def atomic_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".qualification-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def is_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def safe_error(value):
    return value if isinstance(value, str) and re.fullmatch(r"[a-z0-9_]{1,80}", value) else "unspecified_error"


class LocalClient:
    """Direct HTTPConnection uses no ambient proxy and never follows redirects."""
    def __init__(self, config, config_path):
        port = config.get("port", 8090)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("invalid_port")
        self.port = port
        self.token = config.get("origin_auth_token")
        token_file = config.get("origin_auth_token_file")
        if token_file:
            token_path = Path(token_file)
            if not token_path.is_absolute():
                token_path = Path(config_path).resolve().parent / token_path
            self.token = token_path.read_text(encoding="utf-8").strip()
        if self.token is not None and (not isinstance(self.token, str) or not self.token
                                       or "\r" in self.token or "\n" in self.token):
            raise ValueError("invalid_origin_auth")

    def request(self, method, path, payload=None, raw_body=None):
        if (method, path) not in {("GET", "/health"), ("GET", "/models"),
                                  ("GET", "/ready"), ("POST", "/generate")}:
            raise ValueError("invalid_endpoint")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token is not None:
            headers["Authorization"] = "Bearer " + self.token
        body = raw_body
        if payload is not None:
            if raw_body is not None:
                raise ValueError("ambiguous_body")
            body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        if body is not None and len(body) > 65537:
            raise ValueError("request_limit")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=75)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("response_limit")
            return response.status, json.loads(raw)
        finally:
            connection.close()


def qualify(config, root, expected_source_sha, expected_contract_sha, client,
            expected_configured_count=49):
    root = Path(root)
    report = {"schema": "szl.modelhost-qualification/v1", "generated_utc": utc_now(),
              "host": config.get("host_label"), "unsigned": True, "operational_only": True,
              "quality_assessed": False, "prompt_or_output_text_retained": False,
              "checks": [], "representative_generations": [], "source_checks": {},
              "versions": {}, "operational_pass": False, "readiness_pass": False,
              "fully_ready": False}
    for package in ("torch", "transformers", "peft", "huggingface-hub", "safetensors", "accelerate"):
        try:
            report["versions"][package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            report["versions"][package] = None

    def check(name, passed, **details):
        report["checks"].append({"name": name, "passed": bool(passed), **details})
        return bool(passed)

    def request(method, path, **kwargs):
        try:
            status, body = client.request(method, path, **kwargs)
            if type(status) is not int or not isinstance(body, dict):
                raise ValueError("invalid_response")
            return status, body
        except Exception as exc:
            check("transport_" + path.strip("/"), False, exception_type=type(exc).__name__)
            return 0, {}

    for filename, expected in (("szl_modelhost.py", expected_source_sha),
                               ("contract.py", expected_contract_sha)):
        actual = None
        try:
            actual = digest_file(root / filename)
        except OSError:
            pass
        passed = is_sha(expected) and actual is not None and hmac.compare_digest(actual, expected)
        report["source_checks"][filename] = {"expected_sha256": expected,
                                                "actual_sha256": actual, "passed": passed}
        check("source_" + filename, passed)

    health_status, health = request("GET", "/health")
    catalog_status, catalog = request("GET", "/models")
    ready_status, ready = request("GET", "/ready")
    boot_id = health.get("boot_id")
    report["boot_id"] = boot_id
    report["readiness"] = {"http_status": ready_status, "body": ready}
    report["readiness_pass"] = ready_status == 200 and ready.get("ready") is True
    check("liveness_v2_initialized", health_status == 200 and health.get("schema") == SERVER_SCHEMA
          and health.get("alive") is True and health.get("initialization_complete") is True
          and isinstance(boot_id, str) and bool(boot_id))
    check("catalog_v2_same_boot", catalog_status == 200 and catalog.get("schema") == SERVER_SCHEMA
          and catalog.get("boot_id") == boot_id)
    check("readiness_v2_same_boot", ready_status in (200, 503) and ready.get("schema") == SERVER_SCHEMA
          and ready.get("boot_id") == boot_id
          and (ready.get("ready") is True) == (ready_status == 200))

    receipt_path = Path(config.get("receipt_path", root / "receipts" / "latest.json"))
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    try:
        receipt = read_json(receipt_path)
        running_sources = receipt.get("source_sha256", {})
        receipt_ok = (receipt.get("schema") == SERVER_SCHEMA and receipt.get("boot_id") == boot_id
                      and running_sources.get("szl_modelhost.py") == expected_source_sha
                      and running_sources.get("contract.py") == expected_contract_sha)
        report["running_source_sha256"] = {name: running_sources.get(name)
                                           for name in ("szl_modelhost.py", "contract.py", "model_lock.json")}
    except Exception:
        receipt_ok = False
    check("running_receipt_matches_sources_and_boot", receipt_ok)

    manifest = config.get("manifest")
    manifest_ok = (isinstance(manifest, list) and len(manifest) == expected_configured_count
                   and all(isinstance(repo, str) and "/" in repo for repo in manifest)
                   and catalog.get("manifest") == manifest
                   and catalog.get("configured_count") == expected_configured_count
                   and ready.get("configured_count") == expected_configured_count)
    check("full_manifest_preserved", manifest_ok, expected_count=expected_configured_count,
          observed_count=catalog.get("configured_count"))
    models = catalog.get("models", {})
    exclusions = catalog.get("intentional_exclusions", {})
    if not isinstance(models, dict) or not isinstance(exclusions, dict) or not manifest_ok:
        return report
    expected = {repo.rsplit("/", 1)[-1]: repo for repo in manifest}
    required = set(expected) - set(exclusions)
    check("manifest_model_rows_complete", len(expected) == expected_configured_count
          and set(models) == set(expected) and set(exclusions) <= set(expected))
    check("required_denominator_preserved", bool(required)
          and ready.get("required_count") == len(required)
          and ready.get("intentional_exclusions") == sorted(exclusions))
    groups = {}
    failures = []
    for name in sorted(required):
        row = models.get(name, {})
        if (not isinstance(row, dict) or row.get("status") != "loaded"
                or row.get("repo") != expected[name] or row.get("identity_verified") is not True
                or row.get("canary_ok") is not True or row.get("canary_fresh") is not True
                or not is_sha(row.get("artifact_fingerprint"))
                or not isinstance(row.get("base"), str) or not row.get("base")
                or not isinstance(row.get("base_revision"), str) or not row.get("base_revision")):
            failures.append(name)
            continue
        group = row["base"] + "@" + row["base_revision"]
        groups.setdefault(group, []).append(name)
    check("all_required_models_identity_and_canary_verified", not failures,
          required_count=len(required), failures=failures)
    report["intentional_exclusions"] = exclusions
    report["configured_count"] = expected_configured_count
    report["required_count"] = len(required)
    if not groups or not all(item["passed"] for item in report["checks"]):
        return report

    representative = sorted(required)[0]
    identity = models[representative]["artifact_fingerprint"]
    basic = {"model": representative, "prompt": "Operational check.", "max_new_tokens": 1}

    def negative(name, expected_status, expected_error, payload=None, raw_body=None):
        status, body = request("POST", "/generate", payload=payload, raw_body=raw_body)
        check(name, status == expected_status and body.get("err") == expected_error,
              expected_status=expected_status, observed_status=status,
              observed_error=safe_error(body.get("err")))

    negative("unknown_model_rejected", 404, "unknown_model",
             {**basic, "model": "__qualification_unknown_" + uuid.uuid4().hex})
    negative("boolean_token_count_rejected", 400, "invalid_max_new_tokens",
             {**basic, "max_new_tokens": True})
    negative("excess_output_tokens_rejected", 400, "invalid_max_new_tokens",
             {**basic, "max_new_tokens": config.get("max_new_tokens", 256) + 1})
    negative("oversized_body_rejected", 413, "body_too_large", raw_body=b"x" * 65537)
    wrong_identity = ("0" if identity != "0" * 64 else "1") * 64
    negative("wrong_artifact_identity_rejected", 409, "artifact_identity_mismatch",
             {**basic, "expected_artifact_fingerprint": wrong_identity})
    token_probe = "a " * max(3000, config.get("max_input_tokens", 2048) + 256)
    if len(token_probe) <= config.get("max_prompt_chars", 16384):
        negative("excess_input_tokens_rejected", 413, "input_tokens_exceeded",
                 {**basic, "prompt": token_probe, "expected_artifact_fingerprint": identity})
    else:
        check("excess_input_tokens_rejected", False, reason="probe_exceeds_character_limit")

    for base_key, names in sorted(groups.items()):
        name = sorted(names)[0]
        row = models[name]
        payload = {"model": name, "prompt": "Reply with one short sentence confirming you can respond.",
                   "max_new_tokens": 8, "expected_artifact_fingerprint": row["artifact_fingerprint"]}
        started = time.monotonic()
        status, response = request("POST", "/generate", payload=payload)
        elapsed = round((time.monotonic() - started) * 1000, 3)
        count = response.get("completion_tokens")
        duration = response.get("elapsed_ms")
        output = response.get("generation")
        passed = (status == 200 and response.get("model") == name
                  and response.get("repo") == row.get("repo")
                  and response.get("revision") == row.get("revision")
                  and response.get("artifact_fingerprint") == row["artifact_fingerprint"]
                  and response.get("boot_id") == boot_id
                  and type(count) is int and 1 <= count <= 8 and isinstance(output, str)
                  and type(duration) in (int, float) and math.isfinite(duration) and duration >= 0)
        evidence = {"base_identity": base_key, "model": name, "repo": row["repo"],
                    "revision": row.get("revision"), "artifact_fingerprint": row["artifact_fingerprint"],
                    "http_status": status, "passed": passed, "request_elapsed_ms": elapsed}
        if passed:
            evidence.update(completion_tokens=count, elapsed_ms=duration,
                            output_sha256=hashlib.sha256(output.encode()).hexdigest(),
                            output_characters=len(output))
        else:
            evidence["error"] = safe_error(response.get("err"))
        report["representative_generations"].append(evidence)
        check("representative_generation_" + name, passed)

    final_status, final_ready = request("GET", "/ready")
    check("same_boot_after_generation", final_ready.get("boot_id") == boot_id
          and final_ready.get("schema") == SERVER_SCHEMA and final_status in (200, 503))
    report["readiness"] = {"http_status": final_status, "body": final_ready}
    report["readiness_pass"] = final_status == 200 and final_ready.get("ready") is True
    report["operational_pass"] = all(item["passed"] for item in report["checks"])
    report["fully_ready"] = report["operational_pass"] and report["readiness_pass"]
    report["completed_utc"] = utc_now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-contract-sha", required=True)
    parser.add_argument("--expected-configured-count", type=int, default=49)
    args = parser.parse_args(argv)
    try:
        if not is_sha(args.expected_source_sha) or not is_sha(args.expected_contract_sha):
            raise ValueError("invalid_expected_hash")
        config = read_json(args.config)
        report = qualify(config, args.config.resolve().parent, args.expected_source_sha,
                         args.expected_contract_sha, LocalClient(config, args.config),
                         args.expected_configured_count)
        atomic_report(args.output, report)
        print(json.dumps({"operational_pass": report["operational_pass"],
                          "readiness_pass": report["readiness_pass"], "fully_ready": report["fully_ready"],
                          "boot_id": report.get("boot_id"),
                          "failed_checks": [item["name"] for item in report["checks"] if not item["passed"]]}))
        return 0 if report["operational_pass"] else 2
    except Exception as exc:
        print(json.dumps({"operational_pass": False, "error": "qualification_failed",
                          "exception_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
