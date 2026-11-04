# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Specdecode silhouette pointer: honesty labels, no fabricated speedup."""
from __future__ import annotations

import sys
import types
from pathlib import Path

from szl_serve import selfcheck
from szl_serve.specdecode import (
    LABEL_UNAVAILABLE,
    get_verify_draft,
    probe_specdecode,
    verify_draft_available,
)

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
CARD = (ROOT / "CARD.md").read_text(encoding="utf-8")

REQUIRED_PHRASES = [
    "SPECDECODE=UNAVAILABLE",
    "szl-specdecode",
    "verify_draft",
    "Stephen Lutar",
    "MEASURED-or-null",
    "Conjecture 1",
]


def test_readme_and_card_honesty_phrases():
    for phrase in REQUIRED_PHRASES:
        assert phrase in README, f"README missing: {phrase}"
    assert "SPECDECODE=UNAVAILABLE" in CARD
    assert "szl-specdecode" in CARD
    assert "Stephen Lutar" in CARD or "Stephen P. Lutar" in CARD


def test_docs_do_not_claim_gpu_or_speedup():
    lower = README.lower()
    assert "tokens/s MEASURED" not in README
    assert "x faster than vllm" not in lower
    assert "gpu kernel **live**" not in lower
    assert "SPECDECODE=UNAVAILABLE" in README
    assert "Speedup claim stays **null**" in README or "Speedup **null**" in CARD


def test_probe_missing_package_is_unavailable_noop():
    """Default CI has no szl_specdecode → honest UNAVAILABLE, no raise."""
    if "szl_specdecode" in sys.modules:
        # Already injected by another test; still must not claim GPU/speedup.
        rec = probe_specdecode()
    else:
        assert verify_draft_available() is False
        assert get_verify_draft() is None
        rec = probe_specdecode()
        assert rec["status"] == "UNAVAILABLE"
        assert rec["label"] == LABEL_UNAVAILABLE
        assert rec["called"] is False
        assert rec["verify_draft"] is None
    assert rec["gpu"] == "UNAVAILABLE"
    assert rec["speedup_claim"] is None
    assert rec["energy"] == "UNAVAILABLE"


def test_selfcheck_includes_specdecode_without_claiming_speedup():
    report = selfcheck()
    assert report["ok"] is True
    assert "specdecode" in report
    sd = report["specdecode"]
    assert sd["gpu"] == "UNAVAILABLE"
    assert sd["speedup_claim"] is None
    assert sd["label"] in (LABEL_UNAVAILABLE, "import-LIVE")
    assert sd["status"] in ("UNAVAILABLE", "LIVE")


def test_soft_import_live_when_package_injected(monkeypatch):
    """When szl_specdecode is importable, expose verify_draft; still no GPU claim."""

    def fake_verify_draft(**kwargs):
        return {"status": "ACCEPTED_FULL", "accepted_prefix_len": 1}

    def fake_selfcheck():
        return {"ok": True, "note": "correctness only; no speedup claimed"}

    stub = types.ModuleType("szl_specdecode")
    stub.verify_draft = fake_verify_draft
    stub.selfcheck = fake_selfcheck
    monkeypatch.setitem(sys.modules, "szl_specdecode", stub)

    # Re-bind module-level soft import under the stub.
    import importlib
    import szl_serve.specdecode as sd

    importlib.reload(sd)
    try:
        assert sd.verify_draft_available() is True
        assert sd.get_verify_draft() is fake_verify_draft
        rec = sd.probe_specdecode()
        assert rec["status"] == "LIVE"
        assert rec["label"] == "import-LIVE"
        assert rec["via"] == "szl_specdecode.verify_draft"
        assert rec["gpu"] == "UNAVAILABLE"
        assert rec["speedup_claim"] is None
        assert rec["called"] is True
        assert rec["probe_result"]["ok"] is True
    finally:
        # Restore default (missing) soft-import for sibling tests.
        monkeypatch.delitem(sys.modules, "szl_specdecode", raising=False)
        importlib.reload(sd)
