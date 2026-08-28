# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Hash-chain verify. UNSIGNED unless a key is present. No network."""
from __future__ import annotations

import copy

from szl_serve.energy import (
    EnergyReading,
    LABEL_UNAVAILABLE,
    build_serve_receipt,
    verify_serve_chain,
    wrap_serve,
)
from szl_serve.schema import validate_plan


def _receipt(plan, prev="0" * 64):
    validation = validate_plan(
        plan,
        offered_ids=[c["nodeId"] for c in plan["candidates"]],
        source="MODEL",
    )
    return build_serve_receipt(
        request={"query": plan["query"]},
        output=plan,
        validation=validation,
        energy=EnergyReading(
            joules=None,
            label=LABEL_UNAVAILABLE,
            note="unit test CPU path",
            source="test",
        ),
        prev=prev,
    )


def test_receipt_chain_verifies(plan_model_proposed, plan_valid_abstain):
    r0 = _receipt(plan_model_proposed)
    r1 = _receipt(plan_model_proposed, prev=r0["digest"])
    ok, length, brk = verify_serve_chain([r0, r1])
    assert ok is True
    assert length == 2
    assert brk == -1
    assert r0["signed"] is False
    assert r0["signature"] is None
    assert r0["energy_label"] == LABEL_UNAVAILABLE
    assert r0["lambda"].startswith("Conjecture 1")


def test_tampered_output_hash_breaks_chain(plan_model_proposed):
    r0 = _receipt(plan_model_proposed)
    tampered = copy.deepcopy(r0)
    tampered["output_sha256"] = "0" * 64
    ok, _, brk = verify_serve_chain([tampered])
    assert ok is False
    assert brk == 0


def test_non_measured_receipt_cannot_carry_a_joule(plan_model_proposed):
    validation = validate_plan(
        plan_model_proposed,
        offered_ids=[c["nodeId"] for c in plan_model_proposed["candidates"]],
        source="MODEL",
    )
    receipt = build_serve_receipt(
        request={"q": 1},
        output=plan_model_proposed,
        validation=validation,
        energy=EnergyReading(
            joules=12.0,
            label="UNAVAILABLE",
            note="attempted fabrication must be dropped",
            source="test",
        ),
    )
    assert receipt["energy_joules"] is None
    assert receipt["energy_label"] == LABEL_UNAVAILABLE


def test_wrap_rejects_hallucination_and_still_chains(plan_hallucinated_cited):
    wrapped = wrap_serve(
        request={"query": plan_hallucinated_cited["query"]},
        output=plan_hallucinated_cited,
        offered_ids=[
            "node://khipu-synthetic/0acdc9a6105f1f74",
            "node://khipu-synthetic/1fab10b9385d636a",
        ],
        source="MODEL",
    )
    assert wrapped["ok"] is False
    assert wrapped["disposition"] == "REJECT"
    assert wrapped["accepted_plan"] is None
    assert wrapped["repaired"] is False
    ok, _, _ = verify_serve_chain([wrapped["receipt"]])
    assert ok is True
    assert wrapped["receipt"]["validation_disposition"] == "REJECT"


def test_unsigned_without_key(plan_model_proposed):
    wrapped = wrap_serve(
        request={"query": plan_model_proposed["query"]},
        output=plan_model_proposed,
        offered_ids=[c["nodeId"] for c in plan_model_proposed["candidates"]],
        source="MODEL",
        sign_key=None,
    )
    assert wrapped["receipt"]["signed"] is False
    assert wrapped["receipt"]["signature"] is None
