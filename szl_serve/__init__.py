# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""szl-serve — historical Khipu evidence and governed Atelier migration.

The public OpenAI chat recipe is RETIRED. Dated measurements and immutable
artifact/source pins remain historical evidence, not current serving
qualification. The default recipe prints navigation to the authenticated
A11oy Atelier form and unqualified local llama.cpp / Ollama templates.
It does not send or forward a prompt. Model output remains proposal-only.

This is not a vendor engine. The separate modelhost deployment owns its own
readiness gates. Vendor-engine GPU integrations remain ROADMAP.
szl-forge-lab remains SNAPSHOT, not a trainer or serve target.
energy-attested-runs is 8/8 SIMULATED. Joules are MEASURED from a real NVML
delta or UNAVAILABLE. Λ = Conjecture 1 (advisory), never a theorem.
"""
from __future__ import annotations

from szl_serve.energy import (
    LABEL_MEASURED,
    LABEL_UNAVAILABLE,
    ServeEnergyMeter,
    ServeReceipt,
    build_serve_receipt,
    measure_serve_energy,
    verify_serve_chain,
    wrap_serve,
)
from szl_serve.recipe import (
    ASK_AND_ACT,
    ATELIER_LOCK,
    ATELIER_SERVE_STUDIO,
    DEFAULT_WEIGHT_ID,
    ENERGY_ATTESTED_RUNS,
    FORGE_LAB_PIN,
    GPU_PATH,
    LIVE_CHAT_URL,
    LIVE_SPACE_BASE,
    MEASURED_CPU_SAMPLE,
    WEIGHTS,
    atelier_lock,
    format_recipe,
    llama_cli_command,
    llama_server_command,
    ollama_command,
    openai_shaped_chat,
    recipe_document,
    weight_pin,
)
from szl_serve.kernels import list_estate, probe_estate, selfcheck
from szl_serve.specdecode import (
    LABEL_UNAVAILABLE as SPECDECODE_LABEL_UNAVAILABLE,
    get_verify_draft,
    probe_specdecode,
    verify_draft_available,
)
from szl_serve.schema import (
    DISPOSITION_ACCEPT,
    DISPOSITION_REJECT,
    ValidationResult,
    load_khipu_schema,
    schema_sha256,
    validate_plan,
)

__version__ = "0.1.0"
__all__ = [
    "ASK_AND_ACT",
    "ATELIER_LOCK",
    "ATELIER_SERVE_STUDIO",
    "DEFAULT_WEIGHT_ID",
    "DISPOSITION_ACCEPT",
    "DISPOSITION_REJECT",
    "ENERGY_ATTESTED_RUNS",
    "FORGE_LAB_PIN",
    "GPU_PATH",
    "LABEL_MEASURED",
    "LABEL_UNAVAILABLE",
    "LIVE_CHAT_URL",
    "LIVE_SPACE_BASE",
    "MEASURED_CPU_SAMPLE",
    "ServeEnergyMeter",
    "ServeReceipt",
    "ValidationResult",
    "WEIGHTS",
    "atelier_lock",
    "build_serve_receipt",
    "format_recipe",
    "llama_cli_command",
    "llama_server_command",
    "list_estate",
    "load_khipu_schema",
    "measure_serve_energy",
    "probe_estate",
    "probe_specdecode",
    "get_verify_draft",
    "verify_draft_available",
    "SPECDECODE_LABEL_UNAVAILABLE",
    "selfcheck",
    "ollama_command",
    "openai_shaped_chat",
    "recipe_document",
    "schema_sha256",
    "validate_plan",
    "verify_serve_chain",
    "weight_pin",
    "wrap_serve",
    "__version__",
]
