# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
from __future__ import annotations

import copy
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
