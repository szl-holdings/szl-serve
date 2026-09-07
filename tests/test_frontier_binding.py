from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "frontier" / "hf-wave-2026-09-04.json"


def _binding() -> dict:
    return json.loads(BINDING.read_text(encoding="utf-8"))


def test_frontier_binding_is_fail_closed_and_pinned() -> None:
    binding = _binding()
    assert binding["schema"] == "szl.frontier.binding.v1"
    assert binding["owner"] == "szl-serve"
    assert binding["default_effect"] == "HOLD"
    assert binding["production_promotion"] is False
    assert binding["canonical_frontier_revision"] == "94a039d086d1343d1fcfe5bca617f601006ca05b"


def test_k2_is_evaluation_only_with_exact_source_identity() -> None:
    candidates = {item["id"]: item for item in _binding()["candidates"]}
    k2 = candidates["k2-horizon-mova-36b-a4b-2026-09-03"]
    assert k2["status"] == "EVALUATE"
    assert k2["authority"] == "proposal-and-evidence-only"
    assert k2["source_revision"] == "05cab0a4d7150c1c460a000b37ff40cc1af2feaa"
    assert k2["artifact_fingerprint"] == "259e31e5a7143d4f6cca70ed238296e9374b0a51aa497563f62e10af990ec9e2"
    assert "no model-to-action authority bypass" in k2["gates"]


def test_vaani_cannot_escape_gated_hold() -> None:
    candidates = {item["id"]: item for item in _binding()["candidates"]}
    vaani = candidates["vaani-noise-event-2026-08-07"]
    assert vaani["status"] == "GATED_HOLD"
    assert vaani["authority"] == "evidence-input-only"
    assert "authorized Hub gate acceptance" in vaani["gates"]
    assert "no speech-to-action bypass" in vaani["gates"]
