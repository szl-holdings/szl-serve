# SPDX-License-Identifier: Apache-2.0
"""Serve recipe actually probes the kernel estate."""
from __future__ import annotations

import sys
import types

import pytest

from szl_serve import list_estate, probe_estate, selfcheck
from szl_serve import kernels
from szl_serve.kernels import probe_member


REQUIRED = [
    "szl-kernels",
    "szl-receipt-attn",
    "szl-maskmod",
    "szl-block-kv",
    "YARQA-ATTN",
    "szl-governed-norm",
    "szl-lambda-gate",
    "szl-ouroboros",
    "szl-invariants",
    "szl-formulas",
    "szl-blocked",
    "szl-govsign",
    "szl-provctl",
    "szl-nemo",
    "governed-inference-meter",
    "szl-serve",
]


def test_estate_catalog_complete():
    assert set(e["key"] for e in list_estate()) == set(REQUIRED)


@pytest.fixture
def unavailable_estate(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(kernels.importlib, "import_module", missing)
    monkeypatch.setattr(kernels, "cuda_status", lambda: {"status": "UNAVAILABLE"})


def test_selfcheck_cpu_energy_unavailable_and_calls_estate(unavailable_estate):
    report = selfcheck()
    assert report["ok"] is False
    assert report["recipe_ok"] is True
    assert report["estate_ok"] is False
    assert report["status"] == "UNAVAILABLE"
    assert report["energy_joules"] is None
    assert report["energy_label"] == "UNAVAILABLE"
    assert report["gpu"] == "ROADMAP"
    assert report["estate_enumerated"] == 16
    assert report["estate_live"] == 0
    assert report["joblib"] == "QUARANTINED"
    assert report["cuda"]["status"] in ("LIVE", "UNAVAILABLE")


def test_probe_marks_missing_kernel_unavailable(unavailable_estate):
    rec = probe_member(
        {
            "key": "szl-maskmod",
            "module": "szl_maskmod",
            "hub_id": "SZLHOLDINGS/szl-maskmod",
            "probe": "selfcheck",
        }
    )
    assert rec["status"] == "UNAVAILABLE"
    assert rec["called"] is False


def test_injected_kernel_is_actually_called(monkeypatch):
    called = {"n": 0}

    def selfcheck_fn():
        called["n"] += 1
        return {"ok": True}

    stub = types.ModuleType("szl_invariants")
    stub.selfcheck = selfcheck_fn
    monkeypatch.setitem(sys.modules, "szl_invariants", stub)
    rec = probe_member(
        {
            "key": "szl-invariants",
            "module": "szl_invariants",
            "hub_id": "SZLHOLDINGS/szl-invariants",
            "probe": "selfcheck",
        }
    )
    assert called["n"] == 1
    assert rec["status"] == "LIVE"
    assert rec["called"] is True


def test_probe_estate_declares_self_without_fabricating_a_call(unavailable_estate):
    report = probe_estate()
    by_key = {k["key"]: k for k in report["kernels"]}
    assert by_key["szl-serve"]["status"] == "DECLARED"
    assert by_key["szl-serve"]["called"] is False
    assert by_key["szl-serve"]["probe_result"] is None
    assert report["ok"] is False
    assert report["status"] == "UNAVAILABLE"
    assert report["live"] == 0 and report["unavailable"] == 15
    assert report["declared"] == 1 and report["expected_probes"] == 15
    assert report["joblib"] == "QUARANTINED"
    assert report["pickle"] == "QUARANTINED"


def result_probe(monkeypatch, result):
    stub = types.ModuleType("szl_test_kernel")
    stub.selfcheck = lambda: result
    monkeypatch.setitem(sys.modules, stub.__name__, stub)
    return probe_member({"key": "test-kernel", "module": stub.__name__, "probe": "selfcheck"})


@pytest.mark.parametrize("result", [
    False, (False, ["R1"]), {"ok": False}, {"arithmetic_ok": False},
    {"ok": True, "arithmetic_ok": False}, (True, ["R1"]),
    {"ok": True, "label": "failed"}, {"ok": True, "status": "MISMATCH"},
])
def test_negative_probe_verdict_cannot_be_live(monkeypatch, result):
    rec = result_probe(monkeypatch, result)
    assert rec["status"] == "FAILED"
    assert rec["called"] is True


@pytest.mark.parametrize("result", [True, (True, []), {"ok": True}, {"arithmetic_ok": True}])
def test_only_explicit_supported_positive_results_are_live(monkeypatch, result):
    rec = result_probe(monkeypatch, result)
    assert rec["status"] == "LIVE"
    assert rec["called"] is True
    assert rec["evidence_scope"] == "LOCAL_KERNEL_PROBE"


@pytest.mark.parametrize("result", [
    None, {}, "success", 1, {"ok": "true"}, {"ok": 1},
    {"arithmetic_ok": "false"}, {"checks": {"one": True}}, (True, None),
    {"ok": True, "label": "UNAVAILABLE_NO_NVML"},
])
def test_unsupported_or_unavailable_results_do_not_prove_success(monkeypatch, result):
    rec = result_probe(monkeypatch, result)
    assert rec["status"] == "UNAVAILABLE"
    assert rec["called"] is True


def test_probe_runtime_exception_is_failure(monkeypatch):
    stub = types.ModuleType("szl_test_kernel")

    def broken():
        raise RuntimeError("numeric check failed")

    stub.selfcheck = broken
    monkeypatch.setitem(sys.modules, stub.__name__, stub)
    rec = probe_member({"key": "test-kernel", "module": stub.__name__, "probe": "selfcheck"})
    assert rec["status"] == "FAILED" and rec["called"] is True
    assert "numeric check failed" in rec["reason"]


def test_missing_callable_is_not_claimed_called(monkeypatch):
    stub = types.ModuleType("szl_test_kernel")
    monkeypatch.setitem(sys.modules, stub.__name__, stub)
    rec = probe_member({"key": "test-kernel", "module": stub.__name__, "probe": "selfcheck"})
    assert rec["status"] == "UNAVAILABLE" and rec["called"] is False


@pytest.mark.parametrize("verdict,status,expected_ok", [
    (True, "LIVE", True), (False, "FAILED", False), (None, "DEGRADED", False),
])
def test_aggregate_requires_all_external_probes(monkeypatch, verdict, status, expected_ok):
    entries = [
        {"key": "one", "module": "szl_probe_one", "probe": "selfcheck"},
        {"key": "two", "module": "szl_probe_two", "probe": "selfcheck"},
        {"key": "szl-serve", "module": "szl_serve", "probe": "selfcheck"},
    ]
    for entry, value in zip(entries, [True, verdict]):
        stub = types.ModuleType(entry["module"])
        stub.selfcheck = lambda value=value: value
        monkeypatch.setitem(sys.modules, stub.__name__, stub)
    monkeypatch.setattr(kernels, "ESTATE", tuple(entries))
    monkeypatch.setattr(kernels, "cuda_status", lambda: {"status": "UNAVAILABLE"})
    report = probe_estate()
    assert report["ok"] is expected_ok and report["status"] == status
    assert report["any_available"] is True
    assert report["expected_probes"] == 2 and report["declared"] == 1
    assert selfcheck()["ok"] is expected_ok


def test_kernels_cli_fails_when_only_recipe_is_available(unavailable_estate, capsys):
    from szl_serve.cli import main

    assert main(["kernels"]) == 1
    assert '"estate_ok": false' in capsys.readouterr().out


def test_recipe_validity_requires_exact_schema_pin(unavailable_estate, monkeypatch):
    from szl_serve import schema

    monkeypatch.setattr(schema, "schema_sha256", lambda: "a" * 64)
    report = selfcheck()
    assert report["recipe_ok"] is False
    assert report["ok"] is False and report["status"] == "FAILED"


def test_import_failure_is_not_confused_with_missing_dependency(monkeypatch):
    def broken(name):
        raise RuntimeError("module initialization failed")

    monkeypatch.setattr(kernels.importlib, "import_module", broken)
    rec = probe_member({"key": "broken", "module": "broken", "probe": "selfcheck"})
    assert rec["status"] == "FAILED" and rec["called"] is False
