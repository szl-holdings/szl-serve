# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Honest energy wrap + hash-chained serve receipt.

Semantics match ``szl-energy-attest``: MEASURED joules only from a real NVML
delta. Otherwise ``joules=null`` and ``label=UNAVAILABLE``. Never invent a
joule. Never fake DSSE — the receipt is UNSIGNED unless a signing key is
actually present.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from szl_serve.recipe import DEFAULT_WEIGHT_ID, weight_pin
from szl_serve.schema import ValidationResult, validate_plan

LABEL_MEASURED = "MEASURED"
LABEL_UNAVAILABLE = "UNAVAILABLE"
GENESIS_PREV = "0" * 64
RECEIPT_SCHEMA = "szl_serve/receipt@1"
LAMBDA_NOTE = "Conjecture 1 (advisory; trust never 100%)"

_BODY_FIELDS = (
    "schema",
    "request_sha256",
    "output_sha256",
    "model_pin",
    "validation_disposition",
    "energy_joules",
    "energy_label",
    "lambda",
    "signed",
    "note",
)


def _finite(x: Any) -> Optional[float]:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    xf = float(x)
    return xf if math.isfinite(xf) else None


def _canon(obj: Any) -> str:
    """Prefer szl-energy-attest canonical hash when importable; else SHA-256."""
    try:
        from szl_energy_attest import sha256_canon  # type: ignore

        digest = sha256_canon(obj)
        if isinstance(digest, str):
            return digest
    except Exception:
        pass
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_canon_json(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256_bytes(blob)


def nvml_available() -> bool:
    try:
        from szl_energy_attest import nvml_available as _nvml  # type: ignore

        return bool(_nvml())
    except Exception:
        pass
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        n = int(pynvml.nvmlDeviceGetCount())
        pynvml.nvmlShutdown()
        return n > 0
    except Exception:
        return False


@dataclass
class EnergyReading:
    joules: Optional[float]
    label: str
    note: str
    source: str

    def to_dict(self) -> dict:
        return {
            "joules": self.joules,
            "label": self.label,
            "note": self.note,
            "source": self.source,
        }


class ServeEnergyMeter:
    """Context manager: MEASURED from a real NVML counter delta, else UNAVAILABLE.

    Wraps ``szl_energy_attest.measure_block`` when that package is importable.
    Otherwise a tiny local pynvml probe. An empty / CPU path is UNAVAILABLE —
    never a fabricated joule, never a CPU RAPL guess.
    """

    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self.reading = EnergyReading(
            joules=None,
            label=LABEL_UNAVAILABLE,
            note="meter not started",
            source="unstarted",
        )
        self._attest_cm = None
        self._energy_mj0: Optional[int] = None
        self._handle = None
        self._pynvml = None

    def __enter__(self) -> "ServeEnergyMeter":
        try:
            from szl_energy_attest import measure_block  # type: ignore

            self._attest_cm = measure_block(device_index=self.device_index)
            self._attest_cm.__enter__()
            return self
        except Exception:
            self._attest_cm = None
        try:
            import pynvml  # type: ignore

            pynvml.nvmlInit()
            if int(pynvml.nvmlDeviceGetCount()) <= self.device_index:
                return self
            handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
            self._energy_mj0 = int(pynvml.nvmlDeviceGetTotalEnergyConsumption(handle))
            self._handle = handle
            self._pynvml = pynvml
        except Exception:
            self._energy_mj0 = None
            self._handle = None
            self._pynvml = None
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._attest_cm is not None:
            try:
                self._attest_cm.__exit__(exc_type, exc, tb)
                res = getattr(self._attest_cm, "result", None)
                joules = getattr(res, "joules", None) if res is not None else None
                label = getattr(res, "label", None) if res is not None else None
                mj = _finite(joules)
                if label == LABEL_MEASURED and mj is not None and mj > 0:
                    self.reading = EnergyReading(
                        joules=round(mj, 6),
                        label=LABEL_MEASURED,
                        note="MEASURED NVML delta via szl-energy-attest.",
                        source="szl_energy_attest",
                    )
                else:
                    self.reading = EnergyReading(
                        joules=None,
                        label=LABEL_UNAVAILABLE,
                        note="szl-energy-attest present; no fresh NVML delta. joules=null.",
                        source="szl_energy_attest",
                    )
            except Exception:
                self.reading = EnergyReading(
                    joules=None,
                    label=LABEL_UNAVAILABLE,
                    note="szl-energy-attest wrap failed closed; joules=null.",
                    source="szl_energy_attest",
                )
            return False

        if self._pynvml is not None and self._handle is not None and self._energy_mj0 is not None:
            try:
                mj1 = int(self._pynvml.nvmlDeviceGetTotalEnergyConsumption(self._handle))
                joules = max(0.0, (mj1 - self._energy_mj0) / 1000.0)
                if joules > 0:
                    self.reading = EnergyReading(
                        joules=round(joules, 6),
                        label=LABEL_MEASURED,
                        note="MEASURED NVML total-energy-consumption delta (board-level).",
                        source="local-pynvml",
                    )
                    return False
            except Exception:
                pass
        self.reading = EnergyReading(
            joules=None,
            label=LABEL_UNAVAILABLE,
            note="NVML unavailable on this box (typical CPU path). joules=null; no joule fabricated.",
            source="local-fallback",
        )
        return False


def measure_serve_energy() -> EnergyReading:
    """Probe this box. CPU / no NVML => UNAVAILABLE. Never invents a joule."""
    with ServeEnergyMeter() as meter:
        pass
    return meter.reading


def _maybe_sign(body: Dict[str, Any], sign_key: Optional[Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """DSSE only when a real key AND szl-receipt are present. Never fake a signature."""
    if sign_key is None:
        return False, None
    try:
        from szl_receipt import Receipt, sign_receipt  # type: ignore

        envelope = sign_receipt(Receipt(kind="szl-serve", body=body), sign_key, organ="szl-serve")
        if envelope is None:
            return False, None
        signed_flag = bool(envelope.get("signed")) if isinstance(envelope, Mapping) else False
        if not signed_flag:
            return False, envelope if isinstance(envelope, dict) else None
        return True, envelope if isinstance(envelope, dict) else None
    except Exception:
        return False, None


def build_serve_receipt(
    *,
    request: Any,
    output: Any,
    validation: ValidationResult,
    energy: Optional[EnergyReading] = None,
    weight_id: str = DEFAULT_WEIGHT_ID,
    prev: str = GENESIS_PREV,
    sign_key: Optional[Any] = None,
    note: str = "",
) -> Dict[str, Any]:
    pin = weight_pin(weight_id)
    energy = energy or measure_serve_energy()
    joules = _finite(energy.joules)
    label = energy.label if energy.label in (LABEL_MEASURED, LABEL_UNAVAILABLE) else LABEL_UNAVAILABLE
    if label != LABEL_MEASURED or joules is None or joules <= 0:
        joules = None
        label = LABEL_UNAVAILABLE

    body = {
        "schema": RECEIPT_SCHEMA,
        "request_sha256": sha256_canon_json(request),
        "output_sha256": sha256_canon_json(output),
        "model_pin": {
            "weight_id": pin.weight_id,
            "repo_id": pin.repo_id,
            "revision": pin.revision,
            "openai_model_id": pin.openai_model_id,
            "filename": pin.filename,
            "lfs_sha256": pin.lfs_sha256,
            "bytes": pin.bytes,
        },
        "validation_disposition": validation.disposition,
        "energy_joules": None if joules is None else round(joules, 6),
        "energy_label": label,
        "lambda": LAMBDA_NOTE,
        "signed": False,
        "note": note
        or energy.note
        or "Serve receipt. UNSIGNED unless a real key is present. Λ = Conjecture 1.",
    }
    signed, signature = _maybe_sign(body, sign_key)
    body["signed"] = bool(signed)
    if not signed:
        body["signed"] = False

    payload_digest = _canon(body)
    digest = _canon({"prev": prev, "payload_digest": payload_digest})
    receipt = dict(body)
    receipt["prev"] = prev
    receipt["payload_digest"] = payload_digest
    receipt["digest"] = digest
    receipt["signature"] = signature if signed else None
    receipt["energy_source"] = energy.source
    return receipt


ServeReceipt = Dict[str, Any]


def verify_serve_chain(receipts: List[Mapping[str, Any]]) -> Tuple[bool, int, int]:
    """Re-walk the hash chain. Returns (ok, length, first_break_index)."""
    prev = GENESIS_PREV
    for i, raw in enumerate(receipts):
        try:
            if not isinstance(raw, Mapping):
                return False, len(receipts), i
            body = {k: raw[k] for k in _BODY_FIELDS}
            if body.get("energy_label") != LABEL_MEASURED:
                if body.get("energy_joules") is not None:
                    return False, len(receipts), i
            pd = _canon(body)
            dg = _canon({"prev": raw.get("prev"), "payload_digest": pd})
            if pd != raw.get("payload_digest") or dg != raw.get("digest") or raw.get("prev") != prev:
                return False, len(receipts), i
            if body.get("signed") and raw.get("signature") is None:
                return False, len(receipts), i
            prev = raw["digest"]
        except Exception:
            return False, len(receipts), i
    return True, len(receipts), -1


def wrap_serve(
    *,
    request: Any,
    output: Any,
    offered_ids: Optional[list] = None,
    source: str = "MODEL",
    weight_id: str = DEFAULT_WEIGHT_ID,
    prev: str = GENESIS_PREV,
    sign_key: Optional[Any] = None,
    work: Optional[Callable[[], Any]] = None,
) -> Dict[str, Any]:
    """Validate a proposal, wrap energy, mint one hash-chained receipt.

    ``work`` if provided runs inside the energy meter. This helper does not
    call the live Space or download GGUF. Invalid output is REJECT — the
    proposal is not rewritten into a green plan.
    """
    with ServeEnergyMeter() as meter:
        if work is not None:
            work()
    energy = meter.reading
    validation = validate_plan(output, offered_ids=offered_ids, source=source)
    receipt = build_serve_receipt(
        request=request,
        output=output,
        validation=validation,
        energy=energy,
        weight_id=weight_id,
        prev=prev,
        sign_key=sign_key,
    )
    return {
        "disposition": validation.disposition,
        "ok": validation.ok,
        "reasons": list(validation.reasons),
        "repaired": False,
        "proposal": validation.plan,
        "accepted_plan": validation.plan if validation.ok else None,
        "receipt": receipt,
        "energy": energy.to_dict(),
    }
