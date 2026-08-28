# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Plan validation OUTSIDE the weights.

The model output is proposal-only. This controller validates JSON against
the pinned ``khipu.schema.json`` plus the cross-field contract (cited
handles must be a subset of offered candidates; CITE steps must match
``citedNodeIds``; ``brainBinding.status`` stays ``NOT_RESOLVED``).

Invalid plans fail closed (REJECT). They are never silently repaired into
a green NAVIGATE. Real model output must carry ``provenance=MODEL_PROPOSED``,
never ``SYNTHETIC``.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple

from jsonschema.validators import validator_for

DISPOSITION_ACCEPT = "ACCEPT_PROPOSAL"
DISPOSITION_REJECT = "REJECT"

SOURCE_MODEL = "MODEL"
SOURCE_SYNTHETIC = "SYNTHETIC"
SOURCE_UNKNOWN = "UNKNOWN"

SCHEMA_SHA256_PIN = "b95f9927366dae7c5d36cfb7de6e229eb605524318ab642a6aa2292a212170d0"
SCHEMA_BYTES_PIN = 6262

_SCHEMA_CACHE: Optional[dict] = None
_VALIDATOR_CACHE = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def schema_path() -> Path:
    path = _repo_root() / "schemas" / "khipu.schema.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"pinned khipu.schema.json missing at {path}. "
            "This repo copies the schema from SZLHOLDINGS/SZL-Khipu-1.5B-GGUF; "
            "it does not live inside the weights."
        )
    return path


def schema_sha256() -> str:
    return hashlib.sha256(schema_path().read_bytes()).hexdigest()


def load_khipu_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        raw = schema_path().read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != SCHEMA_BYTES_PIN or digest != SCHEMA_SHA256_PIN:
            raise RuntimeError(
                "khipu.schema.json pin mismatch: "
                f"bytes={len(raw)} sha256={digest} "
                f"(expected bytes={SCHEMA_BYTES_PIN} sha256={SCHEMA_SHA256_PIN}). "
                "Refusing to validate against a drifted schema."
            )
        _SCHEMA_CACHE = json.loads(raw.decode("utf-8"))
    return _SCHEMA_CACHE


def _validator():
    global _VALIDATOR_CACHE
    if _VALIDATOR_CACHE is None:
        schema = load_khipu_schema()
        _VALIDATOR_CACHE = validator_for(schema)(schema)
    return _VALIDATOR_CACHE


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    disposition: str
    reasons: Tuple[str, ...]
    provenance: Optional[str]
    brain_binding_status: Optional[str]
    # The original plan object is never mutated. Invalid proposals stay invalid.
    plan: Optional[Mapping[str, Any]]

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "disposition": self.disposition,
            "reasons": list(self.reasons),
            "provenance": self.provenance,
            "brain_binding_status": self.brain_binding_status,
            "repaired": False,
        }


def _as_set(ids: Optional[Iterable[str]]) -> Optional[FrozenSet[str]]:
    if ids is None:
        return None
    return frozenset(str(x) for x in ids)


def _cross_field_reasons(
    plan: Mapping[str, Any],
    offered: Optional[FrozenSet[str]],
) -> list[str]:
    """Mirror the Khipu eval cross-field contract. Fail closed; do not repair."""
    reasons: list[str] = []
    candidates = plan.get("candidates") or []
    steps = plan.get("steps") or []
    cited = list(plan.get("citedNodeIds") or [])
    decision = plan.get("decision")
    abstain_reason = plan.get("abstainReason", None)
    plan_cand_ids = [c.get("nodeId") for c in candidates]
    plan_cand_set = set(plan_cand_ids)

    binding = plan.get("brainBinding") or {}
    status = binding.get("status")
    if status != "NOT_RESOLVED":
        reasons.append(
            f"brainBinding.status={status!r} is not NOT_RESOLVED; "
            "the controller resolves handles OUTSIDE the weights"
        )

    if offered is not None:
        for cid in plan_cand_ids:
            if cid not in offered:
                reasons.append(f"fabricated candidate not among offered handles: {cid}")
        for cid in cited:
            if cid not in offered:
                reasons.append(f"hallucinated citedNodeId not among offered handles: {cid}")
        for step in steps:
            nid = step.get("nodeId")
            if nid not in offered:
                reasons.append(f"step nodeId not among offered handles: {nid}")

    for cid in plan_cand_ids:
        if cid is None:
            reasons.append("candidate missing nodeId")
    for step in steps:
        if step.get("nodeId") not in plan_cand_set:
            reasons.append(
                f"step handle {step.get('nodeId')!r} is not among the plan candidates"
            )
    for cid in cited:
        if cid not in plan_cand_set:
            reasons.append(f"hallucinated citedNodeId not among plan candidates: {cid}")

    cite_steps = {s.get("nodeId") for s in steps if s.get("action") == "CITE"}
    if cite_steps != set(cited):
        reasons.append("citedNodeIds != CITE-action step set")

    if decision == "ABSTAIN":
        if cited:
            reasons.append("ABSTAIN with citations")
        if not abstain_reason:
            reasons.append("ABSTAIN with no abstainReason")
    elif decision == "NAVIGATE":
        if len(cited) < 1:
            reasons.append("NAVIGATE with zero citations")
        if abstain_reason is not None:
            reasons.append("NAVIGATE carries an abstainReason")
    else:
        reasons.append(f"unknown decision {decision!r}")

    if plan.get("groundedOnly") is not True:
        reasons.append("groundedOnly must remain true; invented ids fail closed")

    return reasons


def validate_plan(
    plan: Any,
    *,
    offered_ids: Optional[Iterable[str]] = None,
    source: str = SOURCE_UNKNOWN,
) -> ValidationResult:
    """Validate a plan. Never mutates ``plan``. Never repairs it into a green plan.

    ``source``:
      - ``MODEL`` — real model output; ``provenance`` must be ``MODEL_PROPOSED``.
      - ``SYNTHETIC`` — fixture / illustrative example; ``SYNTHETIC`` is allowed.
      - ``UNKNOWN`` — schema + cross-field only (tests, CLI).
    """
    if not isinstance(plan, Mapping):
        return ValidationResult(
            ok=False,
            disposition=DISPOSITION_REJECT,
            reasons=("plan is not a JSON object",),
            provenance=None,
            brain_binding_status=None,
            plan=None,
        )

    # Snapshot so a caller cannot claim we repaired in place.
    original = copy.deepcopy(dict(plan))
    reasons: list[str] = []

    try:
        _validator().validate(original)
    except Exception as exc:  # noqa: BLE001 — any schema failure is a reject
        reasons.append(f"schema: {str(exc).splitlines()[0]}")

    provenance = original.get("provenance")
    if source == SOURCE_MODEL and provenance != "MODEL_PROPOSED":
        reasons.append(
            f"real model output must carry provenance=MODEL_PROPOSED, not {provenance!r}"
        )
    if provenance not in ("SYNTHETIC", "MODEL_PROPOSED", None) and "schema:" not in "".join(reasons):
        reasons.append(f"unknown provenance {provenance!r}")

    reasons.extend(_cross_field_reasons(original, _as_set(offered_ids)))

    binding = original.get("brainBinding") or {}
    ok = len(reasons) == 0
    return ValidationResult(
        ok=ok,
        disposition=DISPOSITION_ACCEPT if ok else DISPOSITION_REJECT,
        reasons=tuple(reasons),
        provenance=provenance if isinstance(provenance, str) else None,
        brain_binding_status=binding.get("status") if isinstance(binding, Mapping) else None,
        plan=original,
    )


def validate_plan_file(
    path: str | Path,
    *,
    offered_ids: Optional[Sequence[str]] = None,
    source: str = SOURCE_UNKNOWN,
) -> ValidationResult:
    with open(path, "r", encoding="utf-8") as fh:
        plan = json.load(fh)
    return validate_plan(plan, offered_ids=offered_ids, source=source)
