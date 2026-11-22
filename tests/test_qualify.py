# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from szl_serve import qualify as qualifier
from szl_serve.qualify import (
    EXPECTED_SOURCE_REPOSITORY,
    QualificationReadError,
    Readback,
    _SameOriginRedirectHandler,
    fetch_json,
    qualify,
)
from szl_serve.cli import main
from szl_serve.recipe import (
    ATELIER_SERVE_STUDIO,
    FORGE_SOURCE_REVISION,
    KHIPU_BYTES,
    KHIPU_FILENAME,
    KHIPU_LFS_SHA256,
    KHIPU_OPENAI_MODEL_ID,
    KHIPU_REPO,
    KHIPU_REVISION,
)


def exact_payloads() -> dict:
    return {
        "api/build-info": {
            "schema": "szl.build-info/v1",
            "build": {
                "repository": EXPECTED_SOURCE_REPOSITORY,
                "state": "OBSERVED",
                "revision": FORGE_SOURCE_REVISION,
            },
        },
        "api/v1/identity": {
            "schema": "szl.hf-free-inference-identity/v1",
            "status": "READY",
            "space": {"id": ATELIER_SERVE_STUDIO, "source_integrity": True},
            "model": {
                "repo": KHIPU_REPO,
                "revision": KHIPU_REVISION,
                "file": KHIPU_FILENAME,
                "size": KHIPU_BYTES,
                "sha256_expected": KHIPU_LFS_SHA256,
                "sha256_loaded": KHIPU_LFS_SHA256,
            },
            "failure_code": None,
        },
        ".well-known/szl-inference-contract.json": {
            "schema": "szl.inference-contract/v1",
            "status": "READY",
            "model": {
                "id": KHIPU_OPENAI_MODEL_ID,
                "repo": KHIPU_REPO,
                "revision": KHIPU_REVISION,
                "file": KHIPU_FILENAME,
                "size": KHIPU_BYTES,
                "sha256": KHIPU_LFS_SHA256,
            },
            "openai_compatible_subset": {"model_id": KHIPU_OPENAI_MODEL_ID},
        },
        "v1/models": {
            "object": "list",
            "data": [{"id": KHIPU_OPENAI_MODEL_ID, "object": "model"}],
        },
    }


def mapping_fetcher(payloads: dict, failing_suffix: str | None = None):
    def fetch(url: str, _timeout: float, _limit: int) -> Readback:
        if failing_suffix and url.endswith(failing_suffix):
            raise QualificationReadError("TRANSPORT_TIMEOUTERROR")
        for suffix, payload in payloads.items():
            if url.endswith(suffix):
                return Readback(copy.deepcopy(payload), url)
        raise AssertionError(f"unexpected URL {url}")

    return fetch


def test_exact_fixture_is_observed_and_hash_is_deterministic():
    fetcher = mapping_fetcher(exact_payloads())
    first = qualify("https://example.test", observed_at="2026-11-02T06:00:00Z", fetcher=fetcher)
    second = qualify("https://example.test", observed_at="2026-11-02T06:00:00Z", fetcher=fetcher)
    assert first == second
    assert first["state"] == "OBSERVED"
    assert len(first["checks"]) == 26
    assert {check["state"] for check in first["checks"]} == {"OBSERVED"}
    assert first["scope"]["provider_write"] is False
    assert first["scope"]["inference_request"] is False
    assert first["serving_ready"] is False
    assert first["serving_state"] == "NOT_QUALIFIED"
    assert first["legacy_route"]["state"] == "UNKNOWN"
    assert len(first["receipt_sha256"]) == 64


def test_current_contract_without_source_repository_stays_unknown():
    payloads = exact_payloads()
    del payloads["api/build-info"]["build"]["repository"]
    result = qualify(
        "https://example.test",
        observed_at="2026-11-02T06:00:00Z",
        fetcher=mapping_fetcher(payloads),
    )
    assert result["state"] == "UNKNOWN"
    check = next(item for item in result["checks"] if item["name"] == "build.source_repository")
    assert check["state"] == "UNKNOWN"


def test_stale_source_and_wrong_model_are_divergent():
    payloads = exact_payloads()
    payloads["api/build-info"]["build"]["revision"] = "0" * 40
    payloads["v1/models"]["data"][0]["id"] = "other/model@" + "1" * 40
    result = qualify(
        "https://example.test",
        observed_at="2026-11-02T06:00:00Z",
        fetcher=mapping_fetcher(payloads),
    )
    assert result["state"] == "DIVERGENT"
    divergent = {item["name"] for item in result["checks"] if item["state"] == "DIVERGENT"}
    assert divergent == {"build.revision", "models.ids"}


def test_lost_response_is_unknown_and_never_retried_by_qualifier():
    calls: list[str] = []
    base = mapping_fetcher(exact_payloads(), failing_suffix="api/v1/identity")

    def counted(url: str, timeout: float, limit: int) -> Readback:
        calls.append(url)
        return base(url, timeout, limit)

    result = qualify("https://example.test", observed_at="2026-11-02T06:00:00Z", fetcher=counted)
    assert result["state"] == "UNKNOWN"
    assert len(calls) == 4
    assert sum(url.endswith("api/v1/identity") for url in calls) == 1
    failed = next(item for item in result["reads"] if item["name"] == "identity")
    assert failed["state"] == "UNKNOWN"
    assert "TIMEOUT" in failed["error"]


class FakeHeaders:
    def __init__(self, content_type: str):
        self.content_type = content_type

    def get_content_type(self) -> str:
        return self.content_type


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        content_type: str = "application/json",
        final_url: str = "https://example.test/x",
    ):
        self.body = body
        self.headers = FakeHeaders(content_type)
        self.final_url = final_url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return self.final_url

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


@pytest.mark.parametrize(
    "response,error",
    [
        (FakeResponse(b"<html>ok</html>", content_type="text/html"), "CONTENT_TYPE_NOT_JSON"),
        (FakeResponse(b"{"), "INVALID_JSON"),
        (FakeResponse(json.dumps([1, 2]).encode()), "JSON_ROOT_NOT_OBJECT"),
        (FakeResponse(b"{}", final_url="https://evil.test/x"), "CROSS_ORIGIN_REDIRECT"),
    ],
)
def test_fetch_json_rejects_non_contract_responses(monkeypatch, response, error):
    monkeypatch.setattr(qualifier, "_open_url", lambda *_args, **_kwargs: response)
    with pytest.raises(QualificationReadError, match=error):
        fetch_json("https://example.test/x", 1.0, 1024)


@pytest.mark.parametrize(
    "body,reason",
    [
        (b'{"source":"old","source":"pinned"}', "DUPLICATE_JSON_KEY"),
        (b'{"source":"same","source":"same"}', "DUPLICATE_JSON_KEY"),
        (b'{"rows":[{"source":"old","source":"new"}]}', "DUPLICATE_JSON_KEY"),
        (b'{"identity":{"revision":"old","revision":"pinned"}}', "DUPLICATE_JSON_KEY"),
        (b'{"quality":NaN}', "NONFINITE_JSON_NUMBER"),
        (b'{"nested":[{"quality":NaN}]}', "NONFINITE_JSON_NUMBER"),
        (b'{"quality":Infinity}', "NONFINITE_JSON_NUMBER"),
        (b'{"quality":-Infinity}', "NONFINITE_JSON_NUMBER"),
        (b'{"quality":1e9999}', "NONFINITE_JSON_NUMBER"),
        (b'{"quality":1e-324}', "UNDERFLOW_JSON_NUMBER"),
    ],
)
def test_fetch_json_denies_ambiguous_or_nonfinite_provider_evidence(
    monkeypatch, body, reason
):
    monkeypatch.setattr(
        qualifier, "_open_url", lambda *_args, **_kwargs: FakeResponse(body)
    )
    with pytest.raises(QualificationReadError, match=f"^{reason}$"):
        fetch_json("https://example.test/x", 1.0, 1024)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (b'{"quality":0.1234567890123456789}', 0.12345678901234568),
        (b'{"quality":1e308}', 1e308),
        (b'{"quality":0e-9999}', 0.0),
    ],
)
def test_finite_json_boundary_numbers_remain_admissible(monkeypatch, raw, expected):
    monkeypatch.setattr(
        qualifier, "_open_url", lambda *_args, **_kwargs: FakeResponse(raw)
    )
    result = fetch_json("https://example.test/x", 1.0, 1024)
    assert type(result.value["quality"]) is float
    assert result.value["quality"] == expected


def test_duplicate_identity_field_stays_unknown_with_other_metadata_observed(
    monkeypatch,
):
    data = exact_payloads()
    calls = []

    def read_metadata(request, _timeout):
        calls.append(request.full_url)
        suffix = request.full_url.removeprefix("https://example.test/")
        if suffix == "api/v1/identity":
            # Conflicting signed-looking fields MUST NOT be last-wins JSON.
            body = b'{"space":{"source_integrity":false,"source_integrity":true}}'
        else:
            body = json.dumps(data[suffix]).encode("utf-8")
        return FakeResponse(body, final_url=request.full_url)

    monkeypatch.setattr(qualifier, "_open_url", read_metadata)
    result = qualify("https://example.test")
    assert result["state"] == "UNKNOWN"
    assert len(calls) == 4
    failed = next(row for row in result["reads"] if row["name"] == "identity")
    assert failed["state"] == "UNKNOWN"
    assert failed["error"] == "DUPLICATE_JSON_KEY"
    assert result["serving_ready"] is False
    assert result["serving_state"] == "NOT_QUALIFIED"


@pytest.mark.parametrize("fake_true", [1, 1.0, "true", None])
def test_numeric_or_text_integrity_cannot_impersonate_boolean(fake_true):
    data = exact_payloads()
    data["api/v1/identity"]["space"]["source_integrity"] = fake_true
    result = qualify("https://example.test", fetcher=mapping_fetcher(data))
    check = next(
        row for row in result["checks"] if row["name"] == "identity.source_integrity"
    )
    assert check["state"] == "DIVERGENT"
    assert result["state"] == "DIVERGENT"
    assert result["serving_ready"] is False


def test_numeric_float_model_size_cannot_impersonate_expected_integer():
    data = exact_payloads()
    data["api/v1/identity"]["model"]["size"] = float(KHIPU_BYTES)
    data[".well-known/szl-inference-contract.json"]["model"]["size"] = float(
        KHIPU_BYTES
    )
    result = qualify("https://example.test", fetcher=mapping_fetcher(data))
    changed = {
        row["name"] for row in result["checks"] if row["state"] == "DIVERGENT"
    }
    assert changed == {"identity.model.size", "contract.model.size"}
    assert result["serving_ready"] is False


def test_fetch_json_rejects_oversized_response(monkeypatch):
    response = FakeResponse(b"{" + b" " * 1024 + b"}")
    monkeypatch.setattr(qualifier, "_open_url", lambda *_args, **_kwargs: response)
    with pytest.raises(QualificationReadError, match="RESPONSE_TOO_LARGE"):
        fetch_json("https://example.test/x", 1.0, 128)


def test_redirect_handler_blocks_cross_origin_before_following():
    handler = _SameOriginRedirectHandler("https://example.test/x")
    with pytest.raises(QualificationReadError, match="CROSS_ORIGIN_REDIRECT"):
        handler.redirect_request(
            qualifier.Request("https://example.test/x"),
            None,
            302,
            "Found",
            {},
            "https://evil.test/x",
        )


@pytest.mark.parametrize("base_url", [
    "https://synthetic-user@example.test",
    "https://synthetic-user:synthetic-pass@example.test",
    "https://@example.test",
])
def test_base_url_rejects_embedded_credentials_before_fetch(base_url):
    calls = []

    def forbidden_fetch(*_args):
        calls.append(True)
        raise AssertionError("user-info URL must be rejected before any GET")

    with pytest.raises(ValueError, match="URL-embedded credentials") as error:
        qualify(base_url, fetcher=forbidden_fetch)
    assert "synthetic-pass" not in str(error.value)
    assert not calls


@pytest.mark.parametrize("redirect_url", [
    "https://synthetic-user@example.test/x",
    "https://synthetic-user:synthetic-pass@example.test/x",
    "https://@example.test/x",
])
def test_same_host_redirect_rejects_embedded_credentials(redirect_url):
    handler = _SameOriginRedirectHandler("https://example.test/x")
    with pytest.raises(QualificationReadError, match="CROSS_ORIGIN_REDIRECT"):
        handler.redirect_request(
            qualifier.Request("https://example.test/x"),
            None, 302, "Found", {}, redirect_url,
        )


def test_base_url_rejects_query_or_fragment():
    with pytest.raises(ValueError, match="without query or fragment"):
        qualify("https://example.test/?mutable=yes", fetcher=mapping_fetcher(exact_payloads()))


def test_base_url_rejects_silently_discarded_path():
    with pytest.raises(ValueError, match=r"HTTP\(S\) origin"):
        qualify("https://example.test/prefix", fetcher=mapping_fetcher(exact_payloads()))


def test_cli_writes_receipt_and_returns_nonzero_for_unknown(monkeypatch, tmp_path):
    expected = {"schema": "szl.serve-qualification/v1", "state": "UNKNOWN"}
    monkeypatch.setattr("szl_serve.cli.qualify", lambda *_args, **_kwargs: expected)
    output = tmp_path / "qualification.json"
    assert main(["qualify", "--base-url", "https://example.test", "--output", str(output)]) == 1
    assert json.loads(output.read_text(encoding="utf-8")) == expected

def _retired_payloads() -> dict:
    payloads = exact_payloads()
    route = {
        "method": "POST",
        "path": "/v1/chat/completions",
        "state": "RETIRED",
        "status_code": 410,
        "reason_code": "LEGACY_COMPATIBILITY_ROUTE_RETIRED",
        "successor": "/api/v3/governed-infer",
    }
    payloads["api/v1/identity"]["runtime"] = {
        "openai_compatible_subset": {"chat_completions": copy.deepcopy(route)},
    }
    payloads[".well-known/szl-inference-contract.json"]["openai_compatible_subset"][
        "chat_completions"
    ] = copy.deepcopy(route)
    return payloads


def _route_rows(payloads: dict) -> tuple[dict, dict]:
    return (
        payloads["api/v1/identity"]["runtime"]["openai_compatible_subset"]["chat_completions"],
        payloads[".well-known/szl-inference-contract.json"]["openai_compatible_subset"][
            "chat_completions"
        ],
    )


def _observe(payloads: dict) -> dict:
    return qualify(
        "https://example.test",
        observed_at="2026-11-02T06:00:00Z",
        fetcher=mapping_fetcher(payloads),
    )


def test_matching_identity_and_top_level_ready_do_not_override_retired_route():
    result = _observe(_retired_payloads())
    assert result["state"] == "OBSERVED"
    assert len(result["checks"]) == 26
    assert {check["state"] for check in result["checks"]} == {"OBSERVED"}
    assert result["legacy_route"]["state"] == "RETIRED"
    assert result["legacy_route"]["retirement_observed"] is True
    assert result["legacy_route"]["reason_codes"] == []
    assert result["legacy_route"]["declarations"]["identity"]["status_code"] == 410
    assert result["legacy_route"]["declarations"]["contract"]["state"] == "RETIRED"
    assert result["serving_ready"] is False
    assert result["serving_state"] == "NOT_QUALIFIED"
    assert result["scope"]["inference_request"] is False


@pytest.mark.parametrize("failing_suffix", [
    "api/build-info",
    "api/v1/identity",
    ".well-known/szl-inference-contract.json",
    "v1/models",
])
def test_partial_read_failure_preserves_observed_retirement(failing_suffix):
    calls = []
    fetch = mapping_fetcher(_retired_payloads(), failing_suffix=failing_suffix)

    def counted(url, timeout, limit):
        calls.append(url)
        return fetch(url, timeout, limit)

    result = qualify("https://example.test", fetcher=counted)
    assert result["state"] == "UNKNOWN"
    assert result["legacy_route"]["state"] == "RETIRED"
    assert result["legacy_route"]["retirement_observed"] is True
    assert result["serving_ready"] is False
    assert len(calls) == 4
    assert len(set(calls)) == 4


@pytest.mark.parametrize("changes,reason", [
    ({"state": "READY"}, "IDENTITY_RETIREMENT_STATE_CONFLICT"),
    ({"status_code": 200}, "IDENTITY_RETIREMENT_STATUS_CONFLICT"),
    ({"state": "READY", "status_code": 200}, "DECLARATION_STATE_DISAGREEMENT"),
    ({"successor": "/unreviewed-successor"}, "DECLARATION_SUCCESSOR_DISAGREEMENT"),
])
def test_conflicting_route_declarations_never_hide_retirement(changes, reason):
    payloads = _retired_payloads()
    identity, _contract = _route_rows(payloads)
    identity.update(changes)
    result = _observe(payloads)
    assert result["state"] == "OBSERVED"
    assert result["legacy_route"]["state"] == "CONFLICT"
    assert result["legacy_route"]["retirement_observed"] is True
    assert reason in result["legacy_route"]["reason_codes"]
    assert result["serving_ready"] is False


@pytest.mark.parametrize("field,value", [
    ("method", "GET"),
    ("path", "/different-route"),
])
def test_retirement_is_not_attributed_to_a_different_method_or_path(field, value):
    payloads = _retired_payloads()
    for row in _route_rows(payloads):
        row[field] = value
    result = _observe(payloads)
    assert result["legacy_route"]["state"] == "CONFLICT"
    assert result["legacy_route"]["retirement_observed"] is False
    assert result["serving_ready"] is False


@pytest.mark.parametrize("missing", [
    ("method",),
    ("path",),
    ("state", "status_code"),
])
def test_incomplete_route_identity_or_absent_state_is_unknown(missing):
    payloads = _retired_payloads()
    for row in _route_rows(payloads):
        for key in missing:
            row.pop(key)
    result = _observe(payloads)
    assert result["legacy_route"]["state"] == "UNKNOWN"
    assert result["legacy_route"]["retirement_observed"] is False
    assert result["legacy_route"]["reason_codes"]
    assert result["serving_ready"] is False


@pytest.mark.parametrize("missing", ["state", "status_code"])
def test_one_retirement_marker_remains_negative_evidence(missing):
    payloads = _retired_payloads()
    for row in _route_rows(payloads):
        row.pop(missing)
    result = _observe(payloads)
    assert result["legacy_route"]["state"] == "RETIRED"
    assert result["legacy_route"]["retirement_observed"] is True
    assert result["legacy_route"]["reason_codes"]
    assert result["serving_ready"] is False


@pytest.mark.parametrize("code", ["410", 410.0, True])
def test_status_codes_are_not_coerced_into_valid_declarations(code):
    payloads = _retired_payloads()
    identity, _contract = _route_rows(payloads)
    identity["status_code"] = code
    result = _observe(payloads)
    assert result["legacy_route"]["state"] == "CONFLICT"
    assert "IDENTITY_STATUS_CODE_MALFORMED" in result["legacy_route"]["reason_codes"]
    assert result["serving_ready"] is False


@pytest.mark.parametrize("malformed", [[], "RETIRED", False])
def test_non_object_route_descriptors_are_unknown(malformed):
    payloads = _retired_payloads()
    payloads["api/v1/identity"]["runtime"]["openai_compatible_subset"][
        "chat_completions"
    ] = malformed
    payloads[".well-known/szl-inference-contract.json"]["openai_compatible_subset"][
        "chat_completions"
    ] = malformed
    result = _observe(payloads)
    assert result["legacy_route"]["state"] == "UNKNOWN"
    assert result["legacy_route"]["retirement_observed"] is False
    assert result["serving_ready"] is False


def test_matching_nonretired_declarations_do_not_qualify_serving():
    payloads = _retired_payloads()
    for row in _route_rows(payloads):
        row.update(state="READY", status_code=200)
        row.pop("reason_code")
        row.pop("successor")
    result = _observe(payloads)
    assert result["state"] == "OBSERVED"
    assert result["legacy_route"]["state"] == "DECLARED"
    assert result["legacy_route"]["retirement_observed"] is False
    assert result["serving_ready"] is False
    assert result["serving_state"] == "NOT_QUALIFIED"


def test_route_observations_are_bound_into_the_receipt_digest():
    absent = _observe(exact_payloads())
    retired = _observe(_retired_payloads())
    assert absent["checks"] == retired["checks"]
    assert absent["state"] == retired["state"] == "OBSERVED"
    assert absent["receipt_sha256"] != retired["receipt_sha256"]
    for receipt in (absent, retired):
        unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        encoded = json.dumps(
            unsigned, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
        assert hashlib.sha256(encoded).hexdigest() == receipt["receipt_sha256"]


def test_qualification_reads_only_declared_metadata_gets_and_never_follows_successor(monkeypatch):
    payloads = _retired_payloads()
    for row in _route_rows(payloads):
        row["successor"] = "https://example.invalid/must-not-be-contacted"
    calls = []

    def open_metadata(request, _timeout):
        calls.append((request.get_method(), request.full_url))
        suffix = request.full_url.removeprefix("https://example.test/")
        assert suffix in payloads, request.full_url
        return FakeResponse(
            json.dumps(payloads[suffix]).encode("utf-8"),
            final_url=request.full_url,
        )

    monkeypatch.setattr(qualifier, "_open_url", open_metadata)
    result = qualify("https://example.test")
    assert result["legacy_route"]["state"] == "RETIRED"
    assert calls == [
        ("GET", "https://example.test/api/build-info"),
        ("GET", "https://example.test/api/v1/identity"),
        ("GET", "https://example.test/.well-known/szl-inference-contract.json"),
        ("GET", "https://example.test/v1/models"),
    ]
    assert result["scope"]["provider_write"] is False
    assert result["scope"]["inference_request"] is False


def test_cli_matching_identity_without_route_declarations_is_not_success(monkeypatch, capsys):
    def fixture_qualification(base_url, **kwargs):
        return qualify(
            base_url,
            observed_at="2026-11-17T00:00:00Z",
            fetcher=mapping_fetcher(exact_payloads()),
            **kwargs,
        )

    monkeypatch.setattr("szl_serve.cli.qualify", fixture_qualification)
    assert main(["qualify", "--base-url", "https://example.test", "--output", "-"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "OBSERVED"
    assert len(payload["checks"]) == 26
    assert payload["legacy_route"]["state"] == "UNKNOWN"
    assert payload["serving_ready"] is False
