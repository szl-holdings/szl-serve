# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Serve-side kernel estate: explicit local probe verdicts, never inferred readiness.

GPU / vLLM remain ROADMAP. joblib/pickle are not load paths. Energy stays
MEASURED-only via governed-inference-meter when that package is present.
"""
from __future__ import annotations

import importlib
import os
import sys
from typing import Any, Dict, List, Tuple

ESTATE: Tuple[Dict[str, str], ...] = (
    {"key": "szl-kernels", "module": "szl_kernels", "hub_id": "SZLHOLDINGS/szl-kernels", "probe": "selfcheck"},
    {"key": "szl-governed-norm", "module": "szl_governed_norm", "hub_id": "SZLHOLDINGS/szl-governed-norm", "probe": "selfcheck"},
    {"key": "szl-lambda-gate", "module": "szl_lambda_gate", "hub_id": "SZLHOLDINGS/szl-lambda-gate", "probe": "selfcheck"},
    {"key": "governed-inference-meter", "module": "governed_inference_meter", "hub_id": "SZLHOLDINGS/governed-inference-meter", "probe": "selfcheck"},
    {"key": "szl-receipt-attn", "module": "szl_receipt_attn", "hub_id": "SZLHOLDINGS/szl-receipt-attn", "probe": "selfcheck"},
    {"key": "szl-maskmod", "module": "szl_maskmod", "hub_id": "SZLHOLDINGS/szl-maskmod", "probe": "selfcheck"},
    {"key": "szl-block-kv", "module": "szl_block_kv", "hub_id": "SZLHOLDINGS/szl-block-kv", "probe": "selfcheck"},
    {"key": "YARQA-ATTN", "module": "yarqa_attn", "hub_id": "SZLHOLDINGS/YARQA-ATTN", "probe": "selfcheck"},
    {"key": "szl-ouroboros", "module": "szl_ouroboros", "hub_id": "SZLHOLDINGS/szl-ouroboros", "probe": "selfcheck"},
    {"key": "szl-invariants", "module": "szl_invariants", "hub_id": "SZLHOLDINGS/szl-invariants", "probe": "selfcheck"},
    {"key": "szl-formulas", "module": "szl_formulas", "hub_id": "SZLHOLDINGS/szl-formulas", "probe": "selfcheck"},
    {"key": "szl-blocked", "module": "szl_blocked", "hub_id": "SZLHOLDINGS/szl-blocked", "probe": "selfcheck"},
    {"key": "szl-govsign", "module": "szl_govsign", "hub_id": "SZLHOLDINGS/szl-govsign", "probe": "selfcheck"},
    {"key": "szl-provctl", "module": "szl_provctl", "hub_id": "SZLHOLDINGS/szl-provctl", "probe": "selfcheck"},
    {"key": "szl-nemo", "module": "szl_nemo", "hub_id": "SZLHOLDINGS/szl-nemo", "probe": "rule_check"},
    {"key": "szl-serve", "module": "szl_serve", "hub_id": "SZLHOLDINGS/szl-serve", "probe": "selfcheck"},
)


def list_estate() -> List[Dict[str, str]]:
    return [dict(e) for e in ESTATE]


def cuda_status() -> Dict[str, Any]:
    try:
        import torch  # type: ignore

        if bool(torch.cuda.is_available()):
            try:
                name = str(torch.cuda.get_device_name(0))
            except Exception:
                name = "cuda:0"
            return {"status": "LIVE", "device": name}
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "reason": f"{type(exc).__name__}: {exc}",
            "note": "GPU kernels stay ROADMAP; no fake CUDA",
        }
    return {
        "status": "UNAVAILABLE",
        "reason": "torch.cuda.is_available() is False",
        "note": "GPU kernels stay ROADMAP; no fake CUDA",
    }


def _extend_sys_path() -> None:
    extra = os.environ.get("SZL_KERNEL_PATHS", "")
    if not extra:
        return
    for raw in extra.split(os.pathsep):
        path = raw.strip()
        if path and path not in sys.path:
            sys.path.insert(0, path)


def _summarize(result: Any) -> Any:
    if result is None or isinstance(result, (str, int, float, bool)):
        return result
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
        ok, violated = result
        return {"ok": ok, "violated": list(violated) if violated is not None else []}
    if isinstance(result, dict):
        out: Dict[str, Any] = {}
        for key in ("ok", "version", "label", "path", "lambda", "note"):
            if key in result:
                out[key] = result[key]
        if "ok" not in out and "arithmetic_ok" in result:
            out["ok"] = result["arithmetic_ok"]
        return out or {"keys": sorted(result.keys())[:12]}
    return type(result).__name__


def _probe_verdict(result: Any) -> Tuple[str, str]:
    if type(result) is bool:
        return ("LIVE", "explicit_positive_verdict") if result else ("FAILED", "explicit_negative_verdict")
    if isinstance(result, tuple) and len(result) == 2 and type(result[0]) is bool:
        ok, violations = result
        if not ok:
            return "FAILED", "explicit_negative_verdict"
        if not isinstance(violations, (list, tuple)):
            return "UNAVAILABLE", "unsupported_violation_contract"
        return ("FAILED", "reported_violations") if violations else ("LIVE", "explicit_positive_verdict")
    if isinstance(result, dict):
        verdicts = [result[key] for key in ("ok", "arithmetic_ok") if key in result]
        for key in ("status", "label"):
            label = result.get(key)
            label = label.upper() if isinstance(label, str) else ""
            if label.startswith("UNAVAILABLE"):
                return "UNAVAILABLE", "probe_reports_unavailable"
            if label in ("FAILED", "FAIL", "BLOCKED", "MISMATCH", "DEGRADED"):
                return "FAILED", "probe_reports_failure"
        if any(value is False for value in verdicts):
            return "FAILED", "explicit_negative_verdict"
        if verdicts and all(value is True for value in verdicts):
            return "LIVE", "explicit_positive_verdict"
    return "UNAVAILABLE", "unsupported_success_contract"


def _call_probe(mod: Any, probe: str) -> Any:
    if probe == "rule_check":
        return getattr(mod, "rule_check")(
            "hello", "this is MEASURED software, not a score"
        )
    fn = getattr(mod, probe, None)
    if fn is None:
        raise AttributeError(f"{getattr(mod, '__name__', '?')} has no {probe}()")
    return fn()


def probe_member(entry: Dict[str, str]) -> Dict[str, Any]:
    rec = dict(entry)
    rec["joblib"] = "QUARANTINED"
    rec["pickle"] = "QUARANTINED"
    rec["evidence_scope"] = "LOCAL_KERNEL_PROBE"
    if entry["key"] == "szl-serve":
        rec.update(
            {
                "status": "DECLARED",
                "via": "szl_serve.selfcheck",
                "called": False,
                "probe_result": None,
                "reason": "self_entry_not_called_to_avoid_recursive_estate_probe",
            }
        )
        return rec
    try:
        mod = importlib.import_module(entry["module"])
    except ImportError as exc:
        rec.update(
            {
                "status": "UNAVAILABLE",
                "called": False,
                "reason": f"{type(exc).__name__}: {exc}",
            }
        )
        return rec
    except Exception as exc:
        rec.update({"status": "FAILED", "called": False, "reason": f"{type(exc).__name__}: {exc}"})
        return rec
    try:
        if not callable(getattr(mod, entry["probe"], None)):
            rec.update({"status": "UNAVAILABLE", "called": False, "reason": "probe_callable_missing"})
            return rec
        result = _call_probe(mod, entry["probe"])
        status, reason = _probe_verdict(result)
        rec.update(
            {
                "status": status,
                "reason": reason,
                "via": f"{entry['module']}.{entry['probe']}",
                "called": True,
                "probe_result": _summarize(result),
            }
        )
        return rec
    except Exception as exc:
        rec.update(
            {
                "status": "FAILED",
                "called": True,
                "reason": f"{type(exc).__name__}: {exc}",
            }
        )
        return rec


def probe_estate() -> Dict[str, Any]:
    _extend_sys_path()
    kernels = [probe_member(dict(e)) for e in ESTATE]
    live = sum(1 for k in kernels if k.get("status") == "LIVE")
    failed = sum(1 for k in kernels if k.get("status") == "FAILED")
    unavailable = sum(1 for k in kernels if k.get("status") == "UNAVAILABLE")
    declared = sum(1 for k in kernels if k.get("status") == "DECLARED")
    expected = len(kernels) - declared
    ok = expected > 0 and live == expected
    status = "LIVE" if ok else ("FAILED" if failed else ("DEGRADED" if live else "UNAVAILABLE"))
    return {
        "ok": ok,
        "status": status,
        "evidence_scope": "LOCAL_KERNEL_PROBES",
        "any_available": live > 0,
        "live": live,
        "failed": failed,
        "unavailable": unavailable,
        "declared": declared,
        "expected_probes": expected,
        "enumerated": len(kernels),
        "cuda": cuda_status(),
        "joblib": "QUARANTINED",
        "pickle": "QUARANTINED",
        "lambda": "Conjecture 1 (advisory)",
        "kernels": kernels,
    }


def selfcheck() -> Dict[str, Any]:
    """Separate recipe validity from successful probes of the declared estate."""
    from szl_serve.energy import LABEL_UNAVAILABLE, measure_serve_energy
    from szl_serve.recipe import ATELIER_SERVE_STUDIO, GPU_PATH
    from szl_serve.schema import SCHEMA_SHA256_PIN, schema_sha256

    energy = measure_serve_energy()
    estate = probe_estate()
    schema_digest = schema_sha256()
    recipe_ok = (
        energy.label == LABEL_UNAVAILABLE
        and energy.joules is None
        and estate["enumerated"] == len(ESTATE)
        and schema_digest == SCHEMA_SHA256_PIN
    )
    return {
        "ok": recipe_ok and estate["ok"],
        "recipe_ok": recipe_ok,
        "estate_ok": estate["ok"],
        "status": estate["status"] if recipe_ok else "FAILED",
        "evidence_scope": "LOCAL_RECIPE_AND_KERNEL_PROBES",
        "schema_sha256": schema_digest,
        "energy_label": energy.label,
        "energy_joules": energy.joules,
        "gpu": GPU_PATH.get("status", "ROADMAP") if isinstance(GPU_PATH, dict) else GPU_PATH,
        "serve_studio": ATELIER_SERVE_STUDIO,
        "estate_live": estate["live"],
        "estate_enumerated": estate["enumerated"],
        "cuda": estate["cuda"],
        "joblib": "QUARANTINED",
        "lambda": "Conjecture 1 (advisory)",
    }
