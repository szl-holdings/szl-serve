# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Optional soft-import of szl-specdecode behind honesty gates.

Pointer only. Does not rehost CUDA, Medusa, EAGLE, vLLM, or TRT-LLM.
When ``szl_specdecode`` is installed, expose ``verify_draft``. Otherwise
label ``SPECDECODE=UNAVAILABLE``. Never invents a speedup or GPU claim.
Credit Stephen Lutar. Λ = Conjecture 1 (advisory). MEASURED-or-null.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

LABEL_UNAVAILABLE = "SPECDECODE=UNAVAILABLE"
HUB_ID = "SZLHOLDINGS/szl-specdecode"
GITHUB = "https://github.com/szl-holdings/szl-specdecode"
CREDIT = "Stephen Lutar"
LAMBDA = "Conjecture 1 (advisory)"

_verify_draft: Optional[Callable[..., Any]] = None
_import_error: Optional[str] = None

try:
    from szl_specdecode import verify_draft as _vd  # type: ignore

    _verify_draft = _vd
except Exception as exc:  # package missing or broken → honest null
    _verify_draft = None
    _import_error = f"{type(exc).__name__}: {exc}"


def verify_draft_available() -> bool:
    return _verify_draft is not None


def get_verify_draft() -> Optional[Callable[..., Any]]:
    """Return ``szl_specdecode.verify_draft`` when importable, else None."""
    return _verify_draft


def probe_specdecode() -> Dict[str, Any]:
    """Honesty probe: LIVE soft-import or SPECDECODE=UNAVAILABLE. No speedup."""
    base: Dict[str, Any] = {
        "key": "szl-specdecode",
        "hub_id": HUB_ID,
        "github": GITHUB,
        "credit": CREDIT,
        "lambda": LAMBDA,
        "gpu": "UNAVAILABLE",
        "speedup_claim": None,
        "energy": "UNAVAILABLE",
        "note": "draft-verify silhouette pointer; no fabricated tokens/s",
    }
    if _verify_draft is None:
        base.update(
            {
                "status": "UNAVAILABLE",
                "label": LABEL_UNAVAILABLE,
                "called": False,
                "verify_draft": None,
                "reason": _import_error or "szl_specdecode not installed",
            }
        )
        return base

    probe_result: Any = None
    called = False
    try:
        from szl_specdecode import selfcheck as _sc  # type: ignore

        probe_result = _sc()
        called = True
    except Exception as exc:
        probe_result = {"ok": None, "reason": f"{type(exc).__name__}: {exc}"}

    base.update(
        {
            "status": "LIVE",
            "label": "import-LIVE",
            "called": called,
            "via": "szl_specdecode.verify_draft",
            "verify_draft": "szl_specdecode.verify_draft",
            "probe_result": probe_result,
        }
    )
    return base
