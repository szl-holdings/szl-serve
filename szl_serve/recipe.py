# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Canonical serve recipe.

LIVE CPU is the existing MEASURED Hugging Face Space — not a second runtime
invented in this repo. FORGE owns that Space (szl-holdings/szl-forge).
This KERNEL repo pins it, validates plans outside the weights, and wraps
an honest energy receipt.

llama.cpp / Ollama are the airgap twin of that Space, not a vLLM clone.
GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo remain ROADMAP until
MEASURED on named hardware. GPU attention is ROADMAP. Do not invent tokens/s.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
import json

# ---------------------------------------------------------------------------
# Pinned LIVE weight (Khipu GGUF Q4_K_M)
# ---------------------------------------------------------------------------
KHIPU_REPO = "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF"
KHIPU_REVISION = "67d60ec577730747055491640cfb91fc4a4b5d25"
KHIPU_FILENAME = "SZL-Khipu-1.5B-Q4_K_M.gguf"
KHIPU_LFS_SHA256 = "13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a"
KHIPU_BYTES = 986047904
KHIPU_QUANT = "Q4_K_M"
KHIPU_OPENAI_MODEL_ID = f"{KHIPU_REPO}@{KHIPU_REVISION}"

# MEASURED live CPU surface. FORGE-owned. This repo does not take it over.
LIVE_SPACE_ID = "SZLHOLDINGS/szl-model-inference-lab"
LIVE_SPACE_URL = "https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab"
LIVE_SPACE_BASE = "https://szlholdings-szl-model-inference-lab.hf.space"
LIVE_CHAT_URL = f"{LIVE_SPACE_BASE}/v1/chat/completions"
LIVE_MODELS_URL = f"{LIVE_SPACE_BASE}/v1/models"
LIVE_CONTRACT_URL = f"{LIVE_SPACE_BASE}/.well-known/szl-inference-contract.json"
LIVE_IDENTITY_URL = f"{LIVE_SPACE_BASE}/api/v1/identity"
FORGE_SPACE_SOURCE = (
    "https://github.com/szl-holdings/szl-forge/tree/main/spaces/szl-model-inference-lab"
)
FORGE_SOURCE_REVISION = "952e99834c106797254f92a1a46e1627c2847791"

# MEASURED sample (2026-08-28). Raw counts + elapsed. Not a tokens/s claim.
MEASURED_CPU_SAMPLE: Dict[str, Any] = {
    "date": "2026-08-28",
    "surface": LIVE_SPACE_BASE,
    "method": "POST /v1/chat/completions",
    "model": KHIPU_OPENAI_MODEL_ID,
    "completion_tokens": 21,
    "elapsed_ms": 2053,
    "execution_record": "UNSIGNED",
    "energy": {"joules": None, "label": "UNAVAILABLE"},
    "tokens_per_second": None,
    "note": (
        "MEASURED wall elapsed and tokenizer completion count from the FORGE "
        "Space. Not a tokens/s leaderboard. Not proven trust. Energy was not "
        "an NVML delta on that CPU box, so joules stay null / UNAVAILABLE."
    ),
}

DEFAULT_WEIGHT_ID = "khipu"


@dataclass(frozen=True)
class WeightPin:
    weight_id: str
    status: str  # LIVE | ROADMAP
    repo_id: Optional[str]
    revision: Optional[str]
    filename: Optional[str]
    lfs_sha256: Optional[str]
    bytes: Optional[int]
    quant: Optional[str]
    openai_model_id: Optional[str]
    note: str

    def to_dict(self) -> dict:
        return {
            "weight_id": self.weight_id,
            "status": self.status,
            "repo_id": self.repo_id,
            "revision": self.revision,
            "filename": self.filename,
            "lfs_sha256": self.lfs_sha256,
            "bytes": self.bytes,
            "quant": self.quant,
            "openai_model_id": self.openai_model_id,
            "note": self.note,
        }


WEIGHTS: Dict[str, WeightPin] = {
    "khipu": WeightPin(
        weight_id="khipu",
        status="LIVE",
        repo_id=KHIPU_REPO,
        revision=KHIPU_REVISION,
        filename=KHIPU_FILENAME,
        lfs_sha256=KHIPU_LFS_SHA256,
        bytes=KHIPU_BYTES,
        quant=KHIPU_QUANT,
        openai_model_id=KHIPU_OPENAI_MODEL_ID,
        note=(
            "Default LIVE weight. Served by the FORGE-owned MEASURED Space; "
            "airgap twin via llama.cpp/Ollama. Schema validation stays outside "
            "these bytes."
        ),
    ),
    "chaski": WeightPin(
        weight_id="chaski",
        status="ROADMAP",
        repo_id=None,
        revision=None,
        filename=None,
        lfs_sha256=None,
        bytes=None,
        quant=None,
        openai_model_id=None,
        note="Next weight — ROADMAP stub on the same config surface. Not LIVE. No pin fabricated.",
    ),
    "receiptagent": WeightPin(
        weight_id="receiptagent",
        status="ROADMAP",
        repo_id=None,
        revision=None,
        filename=None,
        lfs_sha256=None,
        bytes=None,
        quant=None,
        openai_model_id=None,
        note="Next weight — ROADMAP stub on the same config surface. Not LIVE. No pin fabricated.",
    ),
}

GPU_PATH: Dict[str, Any] = {
    "status": "ROADMAP",
    "engines": ["vLLM", "TGI", "TensorRT-LLM", "SGLang", "Dynamo"],
    "attention": {
        "status": "ROADMAP",
        "note": (
            "GPU attention kernels are ROADMAP. This recipe does not claim "
            "FlashAttention / paged KV / fused GPU attention as LIVE, and "
            "does not invent a tokens/s figure for them."
        ),
        "tokens_per_second": None,
    },
    "until": (
        "MEASURED on named hardware with a real NVML joule delta. "
        "This repo does not vendor-copy those engines and does not claim them LIVE."
    ),
    "tokens_per_second": None,
    "joules": None,
}


def weight_pin(weight_id: str = DEFAULT_WEIGHT_ID) -> WeightPin:
    try:
        return WEIGHTS[weight_id]
    except KeyError as exc:
        raise KeyError(f"unknown weight_id {weight_id!r}; known={sorted(WEIGHTS)}") from exc


def live_openai_curl(prompt: str = "Explain one limit of cryptographic receipts.") -> str:
    """OpenAI-subset call against the MEASURED Space. Dummy bearer only."""
    payload = {
        "model": KHIPU_OPENAI_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 24,
        "stream": False,
    }
    body = json.dumps(payload, separators=(",", ":"))
    return (
        f"curl {LIVE_CHAT_URL} \\\n"
        "  -H \"content-type: application/json\" \\\n"
        "  -H \"authorization: Bearer not-a-secret\" \\\n"
        f"  -d {json.dumps(body)}"
    )


def llama_cli_command(prompt: str = "Navigate: which receipt signed decision d-42?") -> str:
    return (
        f"llama-cli -hf {KHIPU_REPO}:{KHIPU_QUANT} "
        f"-p {prompt!r}"
    )


def llama_server_command(host: str = "127.0.0.1", port: int = 8080) -> str:
    return f"llama-server -hf {KHIPU_REPO}:{KHIPU_QUANT} --host {host} --port {port}"


def ollama_command() -> str:
    return f"ollama run hf.co/{KHIPU_REPO}:{KHIPU_QUANT}"


def openai_shaped_chat() -> Dict[str, Any]:
    """Silhouette: one OpenAI-shaped chat call, one pinned weight, one receipt.

    The LIVE endpoint is the existing Space. Local llama-server is the airgap
    twin of that same pin — not a second public runtime and not vLLM.
    """
    return {
        "silhouette": "one OpenAI-shaped chat call, one pinned weight, one receipt",
        "live": {
            "status": "MEASURED",
            "owner": "FORGE (szl-holdings/szl-forge). KERNEL (this repo) pins + validates + receipts.",
            "not_this_repo": True,
            "base_url": f"{LIVE_SPACE_BASE}/v1",
            "method": "POST",
            "path": "/v1/chat/completions",
            "model": KHIPU_OPENAI_MODEL_ID,
            "streaming": False,
            "tools": False,
            "choices": 1,
            "decoding": "greedy temperature=0, top_p=1",
            "curl": live_openai_curl(),
            "sample": MEASURED_CPU_SAMPLE,
            "space": LIVE_SPACE_URL,
            "contract": LIVE_CONTRACT_URL,
        },
        "airgap_twin": {
            "status": "LIVE_RECIPE",
            "note": (
                "Same pinned Q4_K_M bytes, local llama.cpp / Ollama. "
                "Airgap twin of the Space, not a clone of vLLM/TGI."
            ),
            "llama_cli": llama_cli_command(),
            "llama_server": llama_server_command(),
            "ollama": ollama_command(),
        },
        "gpu": GPU_PATH,
        "weight": weight_pin().to_dict(),
    }


def format_recipe() -> str:
    pin = weight_pin()
    sample = MEASURED_CPU_SAMPLE
    lines = [
        "szl-serve — canonical governed-inference recipe",
        "KERNEL-owned pin + validator + energy receipt. Not a vendor engine.",
        "Λ = Conjecture 1 (advisory). Doctrine v11 LOCKED 749/14/163.",
        "",
        "WHAT THIS IS NOT",
        "  not vLLM, not TGI, not TensorRT-LLM, not SGLang, not Dynamo",
        "  not a tokens/s leaderboard, not proven trust, not a takeover of the HF Space",
        "",
        "LIVE CPU (MEASURED) — existing Space; do not invent a second runtime",
        f"  surface : {LIVE_SPACE_BASE}",
        f"  space   : {LIVE_SPACE_URL}",
        f"  source  : {FORGE_SPACE_SOURCE}",
        f"  forge   : {FORGE_SOURCE_REVISION} (FORGE owns the Space)",
        f"  method  : POST /v1/chat/completions",
        f"  model   : {pin.openai_model_id}",
        f"  GGUF    : {pin.filename}  sha256 {pin.lfs_sha256}  ({pin.bytes} bytes)",
        f"  sample  : {sample['date']}  completion_tokens={sample['completion_tokens']}  "
        f"elapsed_ms={sample['elapsed_ms']}  execution_record={sample['execution_record']}",
        "  energy  : joules=null  label=UNAVAILABLE (CPU; no NVML delta)",
        "  tokens/s: not claimed (raw counts + elapsed only)",
        "",
        live_openai_curl(),
        "",
        "AIRGAP TWIN (same pin, local) — llama.cpp / Ollama, not a vLLM clone",
        f"  {llama_cli_command()}",
        f"  {llama_server_command()}",
        f"  {ollama_command()}",
        "",
        "GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo: ROADMAP",
        "  GPU attention: ROADMAP (no fused/paged-attention LIVE claim; no tokens/s invented)",
        "  until MEASURED on named hardware. No fabricated joule. No fabricated tok/s.",
        "",
        "NEXT WEIGHTS (same config surface, not fake LIVE)",
        "  chaski        ROADMAP — no pin fabricated",
        "  receiptagent  ROADMAP — no pin fabricated",
        "",
        "CONTROLLER",
        "  model output is proposal-only; validate against schemas/khipu.schema.json",
        "  hallucinated citedNodeIds → REJECT (never repaired into a green plan)",
        "  brainBinding.status stays NOT_RESOLVED",
        "  real model provenance = MODEL_PROPOSED (not SYNTHETIC)",
        "  wrap energy: MEASURED NVML delta or UNAVAILABLE; receipt UNSIGNED unless a key exists",
    ]
    return "\n".join(lines) + "\n"


def recipe_document() -> Dict[str, Any]:
    return {
        "schema": "szl_serve/recipe@1",
        "live_cpu": openai_shaped_chat()["live"],
        "airgap_twin": openai_shaped_chat()["airgap_twin"],
        "gpu": GPU_PATH,
        "weights": {k: v.to_dict() for k, v in WEIGHTS.items()},
        "lambda": "Conjecture 1 (advisory; never a theorem)",
        "doctrine": "v11 LOCKED 749/14/163",
    }
