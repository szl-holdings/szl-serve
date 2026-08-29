# SPDX-License-Identifier: Apache-2.0
"""Serve recipe actually probes the kernel estate."""
from __future__ import annotations

import sys
import types

from szl_serve import list_estate, probe_estate, selfcheck
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


def test_selfcheck_cpu_energy_unavailable_and_calls_estate():
    report = selfcheck()
    assert report["ok"] is True
    assert report["energy_joules"] is None
    assert report["energy_label"] == "UNAVAILABLE"
    assert report["gpu"] == "ROADMAP"
    assert report["estate_enumerated"] == 16
    assert report["estate_live"] >= 1
    assert report["joblib"] == "QUARANTINED"
    assert report["cuda"]["status"] in ("LIVE", "UNAVAILABLE")


def test_probe_marks_missing_kernel_unavailable():
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


def test_probe_estate_includes_live_serve():
    report = probe_estate()
    by_key = {k["key"]: k for k in report["kernels"]}
    assert by_key["szl-serve"]["status"] == "LIVE"
    assert by_key["szl-serve"]["called"] is True
    assert report["joblib"] == "QUARANTINED"
    assert report["pickle"] == "QUARANTINED"
