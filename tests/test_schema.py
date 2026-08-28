# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Schema validation outside the weights. No network. No GGUF download."""
from __future__ import annotations

import copy
import json

from szl_serve.schema import (
    DISPOSITION_ACCEPT,
    DISPOSITION_REJECT,
    SCHEMA_SHA256_PIN,
    schema_sha256,
    validate_plan,
)


OFFERED = {
    "node://khipu-synthetic/0acdc9a6105f1f74",
    "node://khipu-synthetic/1fab10b9385d636a",
}


def test_schema_pin_matches_gguf_repo_copy():
    assert schema_sha256() == SCHEMA_SHA256_PIN


def test_valid_navigate_fixture_accepts(plan_valid_navigate):
    result = validate_plan(plan_valid_navigate, offered_ids=OFFERED, source="SYNTHETIC")
    assert result.ok
    assert result.disposition == DISPOSITION_ACCEPT
    assert result.brain_binding_status == "NOT_RESOLVED"
    assert result.provenance == "SYNTHETIC"


def test_valid_abstain_fixture_accepts(plan_valid_abstain):
    offered = {
        "node://khipu-synthetic/aaa1111111111111",
        "node://khipu-synthetic/bbb2222222222222",
    }
    result = validate_plan(plan_valid_abstain, offered_ids=offered, source="SYNTHETIC")
    assert result.ok
    assert result.disposition == DISPOSITION_ACCEPT


def test_hallucinated_cited_node_ids_reject(plan_hallucinated_cited):
    original = copy.deepcopy(plan_hallucinated_cited)
    result = validate_plan(plan_hallucinated_cited, offered_ids=OFFERED, source="MODEL")
    assert result.ok is False
    assert result.disposition == DISPOSITION_REJECT
    assert any("hallucinated" in r for r in result.reasons)
    # Fail closed: the proposal is not rewritten into a green NAVIGATE.
    assert result.to_dict()["repaired"] is False
    assert result.plan == original
    assert result.plan["citedNodeIds"] == ["node://khipu-synthetic/not-offered-deadbeef"]
    assert result.plan["decision"] == "NAVIGATE"


def test_does_not_repair_invalid_plan_into_abstain(plan_hallucinated_cited):
    result = validate_plan(plan_hallucinated_cited, offered_ids=OFFERED, source="MODEL")
    assert result.disposition == DISPOSITION_REJECT
    assert result.plan is not None
    assert result.plan["decision"] != "ABSTAIN" or "not-offered" in str(result.plan)


def test_brain_binding_stays_not_resolved(plan_model_proposed):
    plan = copy.deepcopy(plan_model_proposed)
    plan["brainBinding"]["status"] = "RESOLVED"
    result = validate_plan(plan, offered_ids=OFFERED, source="MODEL")
    assert result.ok is False
    assert result.disposition == DISPOSITION_REJECT
    assert any("NOT_RESOLVED" in r for r in result.reasons)


def test_model_output_must_be_model_proposed_not_synthetic(plan_valid_navigate):
    result = validate_plan(plan_valid_navigate, offered_ids=OFFERED, source="MODEL")
    assert result.ok is False
    assert result.disposition == DISPOSITION_REJECT
    assert any("MODEL_PROPOSED" in r for r in result.reasons)


def test_model_proposed_fixture_accepted_as_model_output(plan_model_proposed):
    result = validate_plan(plan_model_proposed, offered_ids=OFFERED, source="MODEL")
    assert result.ok
    assert result.provenance == "MODEL_PROPOSED"
    assert result.brain_binding_status == "NOT_RESOLVED"


def test_offered_ids_catch_fabricated_candidate_even_if_plan_lists_it(plan_model_proposed):
    plan = copy.deepcopy(plan_model_proposed)
    fake = "node://khipu-synthetic/invented-on-the-spot"
    plan["candidates"].append(
        {
            "nodeId": fake,
            "nodeKind": "CLAIM",
            "label": "UNKNOWN",
            "note": "fabricated candidate",
        }
    )
    plan["steps"].append(
        {"action": "CITE", "nodeId": fake, "rationale": "hallucinated"}
    )
    plan["citedNodeIds"] = [fake]
    # Drop the original CITE so cited set is consistent with CITE steps.
    plan["steps"] = [s for s in plan["steps"] if s["action"] != "CITE" or s["nodeId"] == fake]
    result = validate_plan(plan, offered_ids=OFFERED, source="MODEL")
    assert result.disposition == DISPOSITION_REJECT
    assert any("hallucinated" in r or "fabricated" in r for r in result.reasons)


def test_validate_plan_file_roundtrip(tmp_path, plan_model_proposed):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan_model_proposed), encoding="utf-8")
    from szl_serve.schema import validate_plan_file

    result = validate_plan_file(path, offered_ids=list(OFFERED), source="MODEL")
    assert result.ok
