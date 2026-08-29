# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""szl-serve — KERNEL-owned canonical governed-inference serve recipe.

Silhouette of 2026 serving (vLLM / SGLang / TGI / TensorRT-LLM / llama.cpp /
Dynamo): one OpenAI-shaped chat call, one pinned weight, one receipt.

This is NOT a vendor engine and does not vendor-copy those stacks. LIVE CPU
is the existing MEASURED Hugging Face Space (FORGE-owned). ATELIER lock:
serve studio = SZLHOLDINGS/szl-model-inference-lab only. szl-forge-lab is
SNAPSHOT, not a trainer, not a serve target. This repo pins that lab,
validates proposals outside the weights, and wraps an honest energy
receipt. llama.cpp / Ollama are the airgap twin of that Space, not a
second public runtime and not a vLLM clone.

GPU / vLLM / TGI remain ROADMAP. energy-attested-runs is 8/8 SIMULATED.
Ask & Act is not a live control plane. Joules are MEASURED from a real
NVML delta or UNAVAILABLE. Λ = Conjecture 1 (advisory), never a theorem.
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
