"""Untrusted model proposals need external grounding and must reject cleanly."""
import copy

import pytest

from szl_serve.schema import DISPOSITION_REJECT, validate_plan


def test_model_cannot_supply_its_own_grounding_context(plan_model_proposed):
    result = validate_plan(plan_model_proposed, source="MODEL")
    assert result.disposition == DISPOSITION_REJECT
    assert any("offered_ids" in reason for reason in result.reasons)


def test_empty_external_context_does_not_mean_missing_check(plan_model_proposed):
    result = validate_plan(plan_model_proposed, source="MODEL", offered_ids=[])
    assert result.disposition == DISPOSITION_REJECT
    assert any("not among offered" in reason for reason in result.reasons)


@pytest.mark.parametrize("field,value", [
    ("candidates", ["not an object"]),
    ("candidates", "not an array"),
    ("steps", [None]),
    ("brainBinding", "not an object"),
    ("citedNodeIds", [{"unhashable": True}]),
])
def test_malformed_model_fields_return_reject_without_raising(plan_model_proposed, field, value):
    plan = copy.deepcopy(plan_model_proposed)
    plan[field] = value
    original = copy.deepcopy(plan)
    result = validate_plan(plan, source="MODEL", offered_ids=[])
    assert result.disposition == DISPOSITION_REJECT
    assert result.ok is False
    assert any(reason.startswith("schema:") for reason in result.reasons)
    assert plan == original
    assert result.plan == original
