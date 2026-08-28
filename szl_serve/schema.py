# SPDX-License-Identifier: Apache-2.0
"""Validate Khipu plans outside the weights. Fail closed."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Tuple

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "khipu.schema.json"

def validate_plan(plan: dict) -> Tuple[bool, str]:
    if not isinstance(plan, dict):
        return False, "plan must be an object"
    required = ["planId", "capabilityProfile", "provenance", "query", "contentAccess",
                "candidates", "decision", "steps", "citedNodeIds", "groundedOnly",
                "brainBinding", "controllerBoundary", "abstainReason"]
    missing = [k for k in required if k not in plan]
    if missing:
        return False, f"missing {missing}"
    if plan.get("capabilityProfile") != "SZL-Khipu-1.5B-BrainNavigator":
        return False, "capabilityProfile mismatch"
    if plan.get("provenance") not in ("SYNTHETIC", "MODEL_PROPOSED"):
        return False, "provenance must be SYNTHETIC or MODEL_PROPOSED"
    if plan.get("contentAccess") != "HANDLES_ONLY":
        return False, "contentAccess must be HANDLES_ONLY"
    if plan.get("groundedOnly") is not True:
        return False, "groundedOnly must be true"
    if plan.get("decision") not in ("NAVIGATE", "ABSTAIN"):
        return False, "decision"
    cands = plan.get("candidates") or []
    offered = {c.get("nodeId") for c in cands if isinstance(c, dict)}
    cited = plan.get("citedNodeIds") or []
    extra = [c for c in cited if c not in offered]
    if extra:
        return False, f"hallucinated citations: {extra}"
    bind = plan.get("brainBinding") or {}
    if bind.get("status") != "NOT_RESOLVED":
        return False, "brainBinding.status must stay NOT_RESOLVED (proposal-only)"
    if plan.get("decision") == "ABSTAIN" and not plan.get("abstainReason"):
        return False, "ABSTAIN requires abstainReason"
    return True, "ok"

def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
