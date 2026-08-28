# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def plan_valid_navigate() -> dict:
    return load_fixture("plan_valid_navigate.json")


@pytest.fixture
def plan_valid_abstain() -> dict:
    return load_fixture("plan_valid_abstain.json")


@pytest.fixture
def plan_model_proposed() -> dict:
    return load_fixture("plan_model_proposed.json")


@pytest.fixture
def plan_hallucinated_cited() -> dict:
    return load_fixture("plan_hallucinated_cited.json")
