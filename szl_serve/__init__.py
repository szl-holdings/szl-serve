# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""szl-serve — KERNEL-owned canonical governed-inference serve recipe.

Silhouette of 2026 serving (vLLM / SGLang / TGI / TensorRT-LLM / llama.cpp /
Dynamo): one OpenAI-shaped chat call, one pinned weight, one receipt.

This is NOT a vendor engine and does not vendor-copy those stacks. LIVE CPU
is the existing MEASURED Hugging Face Space (FORGE-owned). This repo pins
that lab, validates proposals outside the weights, and wraps an honest
energy receipt. llama.cpp / Ollama are the airgap twin of that Space, not a
second public runtime and not a vLLM clone.

GPU / vLLM / TGI remain ROADMAP. Joules are MEASURED from a real NVML delta
or UNAVAILABLE. Λ = Conjecture 1 (advisory), never a theorem.
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
    DEFAULT_WEIGHT_ID,
    GPU_PATH,
    LIVE_CHAT_URL,
    LIVE_SPACE_BASE,
    MEASURED_CPU_SAMPLE,
    WEIGHTS,
    format_recipe,
    llama_cli_command,
    llama_server_command,
    ollama_command,
    openai_shaped_chat,
    weight_pin,
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
    "DEFAULT_WEIGHT_ID",
    "DISPOSITION_ACCEPT",
    "DISPOSITION_REJECT",
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
    "build_serve_receipt",
    "format_recipe",
    "llama_cli_command",
    "llama_server_command",
    "load_khipu_schema",
    "measure_serve_energy",
    "ollama_command",
    "openai_shaped_chat",
    "schema_sha256",
    "validate_plan",
    "verify_serve_chain",
    "weight_pin",
    "wrap_serve",
    "__version__",
]
