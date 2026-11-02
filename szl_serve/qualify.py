# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Read-only, fail-closed qualification of the pinned public serve surface.

The qualifier reads identity and contract documents only.  It never sends an
inference request, never writes to a provider, and never turns transport
success into capability evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable, Mapping
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from szl_serve.recipe import (
    ATELIER_SERVE_STUDIO,
    FORGE_SOURCE_REVISION,
    KHIPU_BYTES,
    KHIPU_FILENAME,
    KHIPU_LFS_SHA256,
    KHIPU_OPENAI_MODEL_ID,
    KHIPU_REPO,
    KHIPU_REVISION,
    LIVE_SPACE_BASE,
)

SCHEMA = "szl.serve-qualification/v1"
EXPECTED_SOURCE_REPOSITORY = "szl-holdings/szl-forge"
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_RESPONSE_BYTES = 64 * 1024
ENDPOINTS = {
    "build_info": "/api/build-info",
    "identity": "/api/v1/identity",
    "inference_contract": "/.well-known/szl-inference-contract.json",
    "models": "/v1/models",
}


class QualificationReadError(RuntimeError):
    """One bounded public read could not produce an admissible JSON object."""


@dataclass(frozen=True)
class Readback:
    value: Mapping[str, Any]
    final_url: str


Fetcher = Callable[[str, float, int], Readback]


def _same_origin(expected: str, observed: str) -> bool:
    left = urlparse(expected)
    right = urlparse(observed)
    return (left.scheme.lower(), left.hostname, left.port) == (
        right.scheme.lower(), right.hostname, right.port
    )


class _SameOriginRedirectHandler(HTTPRedirectHandler):
    """Refuse a cross-origin redirect before urllib follows it."""

    def __init__(self, expected_url: str):
        self.expected_url = expected_url
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _same_origin(self.expected_url, newurl):
            raise QualificationReadError("CROSS_ORIGIN_REDIRECT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_url(request: Request, timeout_seconds: float):
    opener = build_opener(_SameOriginRedirectHandler(request.full_url))
    return opener.open(request, timeout=timeout_seconds)


def fetch_json(url: str, timeout_seconds: float, max_response_bytes: int) -> Readback:
    """Fetch one bounded JSON object and reject redirects across origins."""

    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("timeout_seconds must be in (0, 30]")
    if max_response_bytes <= 0 or max_response_bytes > 1024 * 1024:
        raise ValueError("max_response_bytes must be in (0, 1048576]")

    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "szl-serve-qualifier/1"},
        method="GET",
    )
    try:
        with _open_url(request, timeout_seconds) as response:  # nosec B310
            final_url = response.geturl()
            if not _same_origin(url, final_url):
                raise QualificationReadError("CROSS_ORIGIN_REDIRECT")
            content_type = response.headers.get_content_type().lower()
            if content_type != "application/json":
                raise QualificationReadError("CONTENT_TYPE_NOT_JSON")
            raw = response.read(max_response_bytes + 1)
    except QualificationReadError:
        raise
    except Exception as exc:
        raise QualificationReadError(f"TRANSPORT_{type(exc).__name__.upper()}") from exc

    if len(raw) > max_response_bytes:
        raise QualificationReadError("RESPONSE_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationReadError("INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise QualificationReadError("JSON_ROOT_NOT_OBJECT")
    return Readback(value=value, final_url=final_url)


def _check(
    name: str,
    expected: Any,
    observed: Any,
    *,
    missing_unknown: bool = False,
) -> dict[str, Any]:
    if observed is None and missing_unknown:
        state = "UNKNOWN"
    else:
        state = "OBSERVED" if observed == expected else "DIVERGENT"
    return {
        "name": name,
        "state": state,
        "expected": expected,
        "observed": observed,
    }


def _path(value: Mapping[str, Any], *parts: str) -> Any:
    current: Any = value
    for part in parts:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _evaluate(payloads: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    build = payloads["build_info"]
    identity = payloads["identity"]
    contract = payloads["inference_contract"]
    models = payloads["models"]

    model_rows = models.get("data") if isinstance(models.get("data"), list) else []
    model_ids = [row.get("id") for row in model_rows if isinstance(row, Mapping)]
    identity_failure_code = (
        identity["failure_code"] if "failure_code" in identity else "__MISSING__"
    )

    checks = [
        _check("build.schema", "szl.build-info/v1", build.get("schema")),
        _check(
            "build.source_repository",
            EXPECTED_SOURCE_REPOSITORY,
            _path(build, "build", "repository"),
            missing_unknown=True,
        ),
        _check("build.state", "OBSERVED", _path(build, "build", "state")),
        _check("build.revision", FORGE_SOURCE_REVISION, _path(build, "build", "revision")),
        _check("identity.schema", "szl.hf-free-inference-identity/v1", identity.get("schema")),
        _check("identity.status", "READY", identity.get("status")),
        _check("identity.space", ATELIER_SERVE_STUDIO, _path(identity, "space", "id")),
        _check("identity.source_integrity", True, _path(identity, "space", "source_integrity")),
        _check("identity.model.repo", KHIPU_REPO, _path(identity, "model", "repo")),
        _check("identity.model.revision", KHIPU_REVISION, _path(identity, "model", "revision")),
        _check("identity.model.file", KHIPU_FILENAME, _path(identity, "model", "file")),
        _check("identity.model.size", KHIPU_BYTES, _path(identity, "model", "size")),
        _check(
            "identity.model.sha256_expected",
            KHIPU_LFS_SHA256,
            _path(identity, "model", "sha256_expected"),
        ),
        _check(
            "identity.model.sha256_loaded",
            KHIPU_LFS_SHA256,
            _path(identity, "model", "sha256_loaded"),
        ),
        _check("identity.failure_code", None, identity_failure_code),
        _check("contract.schema", "szl.inference-contract/v1", contract.get("schema")),
        _check("contract.status", "READY", contract.get("status")),
        _check("contract.model.id", KHIPU_OPENAI_MODEL_ID, _path(contract, "model", "id")),
        _check("contract.model.repo", KHIPU_REPO, _path(contract, "model", "repo")),
        _check("contract.model.revision", KHIPU_REVISION, _path(contract, "model", "revision")),
        _check("contract.model.file", KHIPU_FILENAME, _path(contract, "model", "file")),
        _check("contract.model.size", KHIPU_BYTES, _path(contract, "model", "size")),
        _check("contract.model.sha256", KHIPU_LFS_SHA256, _path(contract, "model", "sha256")),
        _check(
            "contract.model_id",
            KHIPU_OPENAI_MODEL_ID,
            _path(contract, "openai_compatible_subset", "model_id"),
        ),
        _check("models.object", "list", models.get("object")),
        _check("models.ids", [KHIPU_OPENAI_MODEL_ID], model_ids),
    ]
    return sorted(checks, key=lambda item: item["name"])


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def qualify(
    base_url: str = LIVE_SPACE_BASE,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    observed_at: str | None = None,
    fetcher: Fetcher = fetch_json,
) -> dict[str, Any]:
    """Read all declared surfaces and emit one deterministic qualification receipt."""

    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("base_url must be an absolute HTTP(S) origin without query or fragment")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    timestamp = observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    payloads: dict[str, Mapping[str, Any]] = {}
    reads: list[dict[str, Any]] = []
    for name, path in ENDPOINTS.items():
        url = urljoin(origin + "/", path.lstrip("/"))
        try:
            result = fetcher(url, timeout_seconds, max_response_bytes)
        except QualificationReadError as exc:
            reads.append({"name": name, "url": url, "state": "UNKNOWN", "error": str(exc)})
            continue
        payloads[name] = result.value
        reads.append({"name": name, "url": url, "final_url": result.final_url, "state": "OBSERVED"})

    if len(payloads) == len(ENDPOINTS):
        checks = _evaluate(payloads)
    else:
        missing = sorted(set(ENDPOINTS) - set(payloads))
        checks = [
            {
                "name": f"read.{name}",
                "state": "UNKNOWN",
                "expected": "bounded JSON object",
                "observed": None,
            }
            for name in missing
        ]

    states = {item["state"] for item in checks}
    if "DIVERGENT" in states:
        overall = "DIVERGENT"
    elif "UNKNOWN" in states:
        overall = "UNKNOWN"
    else:
        overall = "OBSERVED"
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "observed_at": timestamp,
        "base_url": origin,
        "state": overall,
        "reads": reads,
        "checks": checks,
        "scope": {
            "mode": "READ_ONLY",
            "provider_write": False,
            "inference_request": False,
            "claims": (
                "identity and declared contract only; not quality, safety, "
                "or production readiness"
            ),
        },
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt
