# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Fail-closed route planning for source-pinned frontier model candidates.

The planner is pure and non-executing. It never downloads weights, imports
remote code, performs inference, mutates a serving target, or grants action
authority. It returns an immutable plan; A11oy remains the consequential-action
admission layer.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any

from szl_serve.recipe import KHIPU_REPO, KHIPU_REVISION

EVALUATION_GATE_KEYS = (
    "source_verification_pass",
    "license_compatibility_pass",
    "runtime_compatibility_pass",
    "remote_code_review_pass",
    "evaluation_authorized",
)
PRODUCTION_GATE_KEYS = EVALUATION_GATE_KEYS + (
    "safety_pass",
    "cost_pass",
    "fallback_pass",
    "governance_pass",
    "reproducibility_pass",
    "nemo_witness_pass",
    "production_approval",
)
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FrontierRoutePlan:
    """A deterministic route proposal. It is never an execution authorization."""

    requested_model_id: str
    requested_revision: str
    selected_model_id: str
    selected_revision: str
    mode: str
    disposition: str
    fallback_used: bool
    reasons: tuple[str, ...]
    executable: bool = False
    model_output_authority: str = "PROPOSAL_ONLY"
    consequential_action_admission_layer: str = "A11oy"

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_model_id": self.requested_model_id,
            "requested_revision": self.requested_revision,
            "selected_model_id": self.selected_model_id,
            "selected_revision": self.selected_revision,
            "mode": self.mode,
            "disposition": self.disposition,
            "fallback_used": self.fallback_used,
            "reasons": list(self.reasons),
            "executable": self.executable,
            "model_output_authority": self.model_output_authority,
            "consequential_action_admission_layer": (
                self.consequential_action_admission_layer
            ),
        }


def _candidate_identity(candidate: Mapping[str, Any]) -> tuple[str, str]:
    model_id = str(candidate.get("model_id") or "").strip()
    revision = str(candidate.get("revision") or "").strip().lower()
    if not model_id:
        raise ValueError("candidate model_id is required")
    if not REVISION_RE.fullmatch(revision):
        raise ValueError("candidate revision must be an immutable 40-hex commit")
    return model_id, revision


def _missing_gates(
    gate_state: Mapping[str, Any],
    required: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        f"{key}:not_passed"
        for key in required
        if gate_state.get(key) is not True
    )


def _fallback(
    *,
    model_id: str,
    revision: str,
    mode: str,
    reasons: tuple[str, ...],
    baseline_model_id: str,
    baseline_revision: str,
) -> FrontierRoutePlan:
    return FrontierRoutePlan(
        requested_model_id=model_id,
        requested_revision=revision,
        selected_model_id=baseline_model_id,
        selected_revision=baseline_revision,
        mode=mode,
        disposition="HOLD_FALLBACK",
        fallback_used=True,
        reasons=reasons or ("fail_closed_default",),
    )


def plan_frontier_route(
    candidate: Mapping[str, Any],
    *,
    mode: str = "production",
    production_promotion_allowed: bool = False,
    baseline_model_id: str = KHIPU_REPO,
    baseline_revision: str = KHIPU_REVISION,
) -> FrontierRoutePlan:
    """Build a fail-closed route plan for one candidate.

    ``evaluation`` may propose a candidate only after every evaluation gate is
    literally ``True``. ``production`` additionally requires every production
    gate, an approved disposition, a verified 64-hex promotion receipt, and an
    explicit caller-side promotion allowance. Returned plans remain
    non-executable and proposal-only.
    """

    if mode not in {"evaluation", "production"}:
        raise ValueError("mode must be 'evaluation' or 'production'")
    if not REVISION_RE.fullmatch(str(baseline_revision).lower()):
        raise ValueError("baseline revision must be an immutable 40-hex commit")

    model_id, revision = _candidate_identity(candidate)
    raw_gate_state = candidate.get("gate_state")
    gate_state = raw_gate_state if isinstance(raw_gate_state, Mapping) else {}
    reasons: list[str] = []

    if candidate.get("authority") != "proposal-only":
        reasons.append("candidate_authority:not_proposal_only")

    if mode == "evaluation":
        reasons.extend(_missing_gates(gate_state, EVALUATION_GATE_KEYS))
        if reasons:
            return _fallback(
                model_id=model_id,
                revision=revision,
                mode=mode,
                reasons=tuple(reasons),
                baseline_model_id=baseline_model_id,
                baseline_revision=str(baseline_revision).lower(),
            )
        return FrontierRoutePlan(
            requested_model_id=model_id,
            requested_revision=revision,
            selected_model_id=model_id,
            selected_revision=revision,
            mode=mode,
            disposition="EVALUATION_ONLY",
            fallback_used=False,
            reasons=("all_evaluation_gates_passed",),
        )

    reasons.extend(_missing_gates(gate_state, PRODUCTION_GATE_KEYS))
    if not production_promotion_allowed:
        reasons.append("production_promotion:disabled")
    if candidate.get("production_disposition") != "APPROVED":
        reasons.append("production_disposition:not_approved")
    receipt = str(candidate.get("promotion_receipt_sha256") or "").lower()
    if not SHA256_RE.fullmatch(receipt):
        reasons.append("promotion_receipt_sha256:missing_or_invalid")

    if reasons:
        return _fallback(
            model_id=model_id,
            revision=revision,
            mode=mode,
            reasons=tuple(reasons),
            baseline_model_id=baseline_model_id,
            baseline_revision=str(baseline_revision).lower(),
        )

    return FrontierRoutePlan(
        requested_model_id=model_id,
        requested_revision=revision,
        selected_model_id=model_id,
        selected_revision=revision,
        mode=mode,
        disposition="PRODUCTION_ROUTE_REVIEWED",
        fallback_used=False,
        reasons=("all_production_gates_and_receipt_passed",),
    )
