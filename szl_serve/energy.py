# SPDX-License-Identifier: Apache-2.0
"""MEASURED NVML joules or honest UNAVAILABLE. Never fabricate a joule."""
from __future__ import annotations
from typing import Optional, Tuple

def measure_or_unavailable() -> Tuple[Optional[float], str]:
    try:
        from szl_energy_attest import measure_joules
        return measure_joules()
    except Exception:
        pass
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mj = pynvml.nvmlDeviceGetTotalEnergyConsumption(handle)
        # snapshot only; a delta requires two samples around work. Without a delta this is not MEASURED work energy.
        return None, "UNAVAILABLE"
    except Exception:
        return None, "UNAVAILABLE"
