# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""CPU energy is UNAVAILABLE. Never invent a joule. No network."""
from __future__ import annotations

from szl_serve.energy import (
    LABEL_MEASURED,
    LABEL_UNAVAILABLE,
    ServeEnergyMeter,
    measure_serve_energy,
    wrap_serve,
)


def test_cpu_energy_unavailable_null_joules():
    reading = measure_serve_energy()
    assert reading.label == LABEL_UNAVAILABLE
    assert reading.joules is None
    assert reading.label != LABEL_MEASURED


def test_meter_context_on_cpu_is_unavailable():
    with ServeEnergyMeter() as meter:
        pass
    assert meter.reading.joules is None
    assert meter.reading.label == LABEL_UNAVAILABLE


def test_wrap_serve_does_not_mint_measured_joules_on_cpu(plan_model_proposed):
    wrapped = wrap_serve(
        request={"query": plan_model_proposed["query"], "candidates": plan_model_proposed["candidates"]},
        output=plan_model_proposed,
        offered_ids=[c["nodeId"] for c in plan_model_proposed["candidates"]],
        source="MODEL",
    )
    assert wrapped["energy"]["joules"] is None
    assert wrapped["energy"]["label"] == LABEL_UNAVAILABLE
    assert wrapped["receipt"]["energy_joules"] is None
    assert wrapped["receipt"]["energy_label"] == LABEL_UNAVAILABLE
    assert wrapped["receipt"]["signed"] is False
    assert wrapped["receipt"]["signature"] is None
