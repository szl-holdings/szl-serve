from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from szl_serve.frontier import (
    EVALUATION_GATE_KEYS,
    PRODUCTION_GATE_KEYS,
    plan_frontier_route,
)
from szl_serve.recipe import KHIPU_REPO, KHIPU_REVISION

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "frontier" / "model-wave-routing-2026-09-08.json"

EXPECTED_CANDIDATES = {
    "zai-org/GLM-5.3-Flash": "eb9eb208eb0d988989d07a6a12d0fdeb5f52574a",
    "deepseek-ai/DeepSeek-V4-Flash-Vision-Exp": (
        "6821d6ad3681a4b137b066b76094fa82ebd0a380"
    ),
    "nvidia/Qwen3.8-Flash-Next-NVFP4": (
        "fc694b54fb0174e0913e6adf86691ef85a4ead47"
    ),
}
EXPECTED_REFERENCES = {
    "zai-org/GLM-5.3": "aca966e4e02791568aa6a4ced368624b3d897f42",
    "Qwen/Qwen3.8-Flash-Next": "de4b8e4d43b917e7706784d8bb445c9af86a3540",
}


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _candidates() -> dict[str, dict]:
    return {row["model_id"]: row for row in _contract()["candidate_routes"]}


def test_route_contract_is_bound_to_the_exact_frontier_chain() -> None:
    upstream = _contract()["upstream_contracts"]
    assert upstream["frontier_registry"]["revision"] == (
        "dcc128140f3873d0ca396b9a83cf0eb5a0102b87"
    )
    assert upstream["forge_qualification"]["revision"] == (
        "ffe66a1aba2c6027e48da6f89cdd5d4fc2f87794"
    )
    assert upstream["nemo_witness"]["revision"] == (
        "38018c7215d8915805c7620341903a472672839e"
    )


def test_baseline_is_the_existing_live_khipu_pin() -> None:
    contract = _contract()
    baseline = contract["baseline"]
    assert contract["default_effect"] == "HOLD"
    assert contract["production_promotion"] is False
    assert contract["model_output_authority"] == "PROPOSAL_ONLY"
    assert contract["consequential_action_admission_layer"] == "A11oy"
    assert baseline["model_id"] == KHIPU_REPO
    assert baseline["revision"] == KHIPU_REVISION
    assert baseline["status"] == "LIVE"
    assert baseline["selection"] == "DEFAULT_FALLBACK"


def test_candidate_and_reference_identities_are_exact_and_disjoint() -> None:
    candidates = _candidates()
    references = {
        row["model_id"]: row for row in _contract()["reference_artifacts"]
    }
    assert {key: value["revision"] for key, value in candidates.items()} == (
        EXPECTED_CANDIDATES
    )
    assert {key: value["revision"] for key, value in references.items()} == (
        EXPECTED_REFERENCES
    )
    assert set(candidates).isdisjoint(references)
    assert all(row["routable"] is False for row in references.values())


@pytest.mark.parametrize("mode", ["evaluation", "production"])
def test_every_current_candidate_falls_back_fail_closed(mode: str) -> None:
    for candidate in _candidates().values():
        plan = plan_frontier_route(
            candidate,
            mode=mode,
            production_promotion_allowed=_contract()["production_promotion"],
        )
        assert plan.disposition == "HOLD_FALLBACK"
        assert plan.fallback_used is True
        assert plan.selected_model_id == KHIPU_REPO
        assert plan.selected_revision == KHIPU_REVISION
        assert plan.executable is False
        assert plan.model_output_authority == "PROPOSAL_ONLY"
        assert plan.consequential_action_admission_layer == "A11oy"


def test_evaluation_route_requires_every_literal_true_gate() -> None:
    candidate = copy.deepcopy(next(iter(_candidates().values())))
    for gate in EVALUATION_GATE_KEYS:
        candidate["gate_state"][gate] = True
    plan = plan_frontier_route(candidate, mode="evaluation")
    assert plan.disposition == "EVALUATION_ONLY"
    assert plan.fallback_used is False
    assert plan.selected_model_id == candidate["model_id"]
    assert plan.executable is False


def test_one_missing_evaluation_gate_forces_baseline_fallback() -> None:
    candidate = copy.deepcopy(next(iter(_candidates().values())))
    for gate in EVALUATION_GATE_KEYS:
        candidate["gate_state"][gate] = True
    candidate["gate_state"]["runtime_compatibility_pass"] = None
    plan = plan_frontier_route(candidate, mode="evaluation")
    assert plan.disposition == "HOLD_FALLBACK"
    assert "runtime_compatibility_pass:not_passed" in plan.reasons


def test_global_promotion_hold_wins_even_if_candidate_gates_are_true() -> None:
    candidate = copy.deepcopy(next(iter(_candidates().values())))
    for gate in PRODUCTION_GATE_KEYS:
        candidate["gate_state"][gate] = True
    candidate["production_disposition"] = "APPROVED"
    candidate["promotion_receipt_sha256"] = "a" * 64
    plan = plan_frontier_route(
        candidate,
        mode="production",
        production_promotion_allowed=False,
    )
    assert plan.disposition == "HOLD_FALLBACK"
    assert "production_promotion:disabled" in plan.reasons


def test_reviewed_production_plan_still_carries_no_execution_authority() -> None:
    candidate = copy.deepcopy(next(iter(_candidates().values())))
    for gate in PRODUCTION_GATE_KEYS:
        candidate["gate_state"][gate] = True
    candidate["production_disposition"] = "APPROVED"
    candidate["promotion_receipt_sha256"] = "b" * 64
    plan = plan_frontier_route(
        candidate,
        mode="production",
        production_promotion_allowed=True,
    )
    assert plan.disposition == "PRODUCTION_ROUTE_REVIEWED"
    assert plan.fallback_used is False
    assert plan.selected_model_id == candidate["model_id"]
    assert plan.executable is False
    assert plan.consequential_action_admission_layer == "A11oy"


def test_mutable_or_missing_candidate_revision_is_rejected() -> None:
    candidate = copy.deepcopy(next(iter(_candidates().values())))
    candidate["revision"] = "main"
    with pytest.raises(ValueError, match="immutable 40-hex"):
        plan_frontier_route(candidate)
