"""GGUF quantization planning (propose-only).

Doctrine (leader-study, #47 read-only; llama.cpp GGUF leaders studied,
NOT executed): quantization choice is a planning decision before it is
a conversion. This module reasons about bits-per-weight constants
DECLARED from llama.cpp documentation (rounded, disclosed) and computes
size estimates; it never converts anything.

Honest limitation, verbatim: size estimation only; real GGUF files carry
metadata overhead not modeled here; no conversion is executed, no
models, files, or binaries are touched, and llama.cpp is never invoked.
Only unquantized sources (F32/F16/BF16) may be planned for quantization;
quantizing-from-quantized is rejected fail-closed.

Propose-only, unsigned; merges are owned by the estate signature wall.
No status claims are made about any other pull request.
"""

from __future__ import annotations

import math
from typing import Dict

SCHEMA_VERSION = "szl.quantplan/v1"
BANNER = "PROPOSAL_ONLY_UNSIGNED"

UNQUANTIZED = ("F32", "BF16", "F16")

# Declared bits-per-weight constants (llama.cpp documentation, rounded).
# These are DECLARED CONSTANTS, not a quality ranking (Kimi W32 amend 2).
KNOWN_QUANTS: Dict[str, float] = {
    "F32": 32.0, "BF16": 16.0, "F16": 16.0,
    "Q8_0": 8.5, "Q6_K": 6.59, "Q5_K_S": 5.5, "Q5_K_M": 5.69,
    "Q4_K_S": 4.5, "Q4_K_M": 4.85, "Q3_K_M": 3.91, "Q3_K_S": 3.5,
    "Q2_K": 3.36, "IQ4_XS": 4.25, "IQ3_M": 3.66, "IQ2_XS": 2.31,
}


class QuantError(ValueError):
    """A quantization plan input is malformed or forbidden."""


def validated_quant(name: str) -> float:
    """Return bits-per-weight for a KNOWN quant; unknown names raise."""
    if not isinstance(name, str) or name not in KNOWN_QUANTS:
        raise QuantError("unknown quant %r; must be one of the declared KNOWN_QUANTS" % (name,))
    return KNOWN_QUANTS[name]


def plan(n_params: int, quant: str, source: str = "F16") -> Dict[str, object]:
    """Plan a quantization estimate. Fails closed on unknown quants,
    non-positive parameter counts, unknown sources, and quantized
    sources (Kimi W32 amend 1: an unknown source raises, it is never
    silently treated as unquantized)."""
    if not isinstance(n_params, int) or isinstance(n_params, bool) or n_params <= 0:
        raise QuantError("n_params must be a positive integer")
    bpw = validated_quant(quant)
    validated_quant(source)  # fail-closed: unknown source raises here
    if source not in UNQUANTIZED:
        raise QuantError("source must be one of %r (quantized sources may not "
                         "be re-quantized)" % (UNQUANTIZED,))
    estimated_bytes = math.ceil(n_params * bpw / 8)
    return {"schema_version": SCHEMA_VERSION, "banner": BANNER,
            "quant": quant, "bits_per_weight": bpw,
            "n_params": n_params, "source": source,
            "estimated_bytes": estimated_bytes,
            "estimate_disclosure": ("ESTIMATE ONLY: declared bits-per-weight, "
                                    "no metadata overhead, no conversion executed")}
