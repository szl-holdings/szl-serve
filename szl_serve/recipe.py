# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Canonical serve recipe.

LIVE CPU is the existing MEASURED Hugging Face Space — not a second runtime
invented in this repo. FORGE owns that Space (szl-holdings/szl-forge).
This KERNEL repo pins it, validates plans outside the weights, and wraps
an honest energy receipt.

ATELIER lock: serve studio = SZLHOLDINGS/szl-model-inference-lab only.
SZLHOLDINGS/szl-forge-lab is SNAPSHOT, not a trainer, not a serve target.
Do not point this recipe at forge-lab. GPU remains ROADMAP.
energy-attested-runs is 8/8 SIMULATED (not MEASURED serve energy).
Ask & Act is not a live control plane.

llama.cpp / Ollama are the airgap twin of that Space, not a vLLM clone.
GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo remain ROADMAP until
MEASURED on named hardware. GPU attention is ROADMAP. Do not invent tokens/s.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
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
# ATELIER lock: this Space is the only serve studio. Do not substitute forge-lab.
ATELIER_SERVE_STUDIO = "SZLHOLDINGS/szl-model-inference-lab"
LIVE_SPACE_ID = ATELIER_SERVE_STUDIO
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

# SNAPSHOT / READ-ONLY evidence console. Not a trainer. Not a serve runtime.
# REACHABLE = transport only. Curriculum BLUEPRINT_NOT_TRAINED.
# Do not point szl-serve at this Space as LIVE, curl, or model pin.
FORGE_LAB_SPACE = "SZLHOLDINGS/szl-forge-lab"
FORGE_LAB_URL = "https://huggingface.co/spaces/SZLHOLDINGS/szl-forge-lab"
FORGE_LAB_PIN: Dict[str, Any] = {
    "id": FORGE_LAB_SPACE,
    "url": FORGE_LAB_URL,
    "class": "SNAPSHOT",
    "presentation": "SNAPSHOT/READ-ONLY evidence console",
    "not_a_trainer": True,
    "not_a_serve_target": True,
    "reachable_means": "transport only",
    "curriculum": "BLUEPRINT_NOT_TRAINED",
    "note": (
        "Do not point szl-serve at forge-lab. No LIVE URL, curl, or model pin. "
        "No endpoint trains, publishes, promotes, or deploys."
    ),
}

# Honesty pin: corpus exists; result is SIMULATED, not MEASURED NVML joules,
# and not a live serve path. CPU serve energy stays UNAVAILABLE unless a real
# NVML delta exists.
ENERGY_ATTESTED_RUNS: Dict[str, Any] = {
    "id": "SZLHOLDINGS/energy-attested-runs",
    "space": "https://huggingface.co/spaces/SZLHOLDINGS/energy-attested-runs",
    "dataset": "https://huggingface.co/datasets/SZLHOLDINGS/energy-attested-runs",
    "result": "8/8",
    "label": "SIMULATED",
    "not_measured_nvml": True,
    "not_a_live_serve_path": True,
    "note": (
        "8/8 SIMULATED. Not MEASURED NVML joules. Not a live serve path. "
        "Do not treat this corpus as this repo's CPU energy evidence."
    ),
}

# a11oy operator tab (Operate / ask). Does not gate, launch, or control this recipe.
ASK_AND_ACT: Dict[str, Any] = {
    "status": "NOT_A_LIVE_CONTROL_PLANE",
    "surface": "a11oy operator tab (Operate / ask)",
    "note": (
        "Ask & Act is not a live control plane. It does not gate, launch, "
        "or control this serve recipe."
    ),
}

ATELIER_LOCK: Dict[str, Any] = {
    "serve_studio": ATELIER_SERVE_STUDIO,
    "serve_studio_only": True,
    "live_cpu": LIVE_SPACE_BASE,
    "model": KHIPU_OPENAI_MODEL_ID,
    "forge_lab": FORGE_LAB_PIN,
    "energy_attested_runs": ENERGY_ATTESTED_RUNS,
    "ask_and_act": ASK_AND_ACT,
    "gpu": "ROADMAP",
}

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


def live_serve_targets() -> tuple[str, ...]:
    """The only public serve studio. forge-lab is never in this tuple."""
    return (ATELIER_SERVE_STUDIO, LIVE_SPACE_BASE, LIVE_SPACE_URL, LIVE_CHAT_URL)


def is_forbidden_serve_target(value: str) -> bool:
    """True if a URL/id would point szl-serve at SNAPSHOT forge-lab."""
    return "szl-forge-lab" in value.lower()


def atelier_lock() -> Dict[str, Any]:
    """Machine-readable ATELIER lock. Serve studio is inference-lab only."""
    return {
        "schema": "szl_serve/atelier_lock@1",
        "serve_studio": ATELIER_SERVE_STUDIO,
        "serve_studio_only": True,
        "live_cpu": LIVE_SPACE_BASE,
        "model": KHIPU_OPENAI_MODEL_ID,
        "forge_lab": dict(FORGE_LAB_PIN),
        "energy_attested_runs": dict(ENERGY_ATTESTED_RUNS),
        "ask_and_act": dict(ASK_AND_ACT),
        "gpu": dict(GPU_PATH),
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

    The LIVE endpoint is the existing Space (ATELIER serve studio only).
    Local llama-server is the airgap twin of that same pin — not a second
    public runtime, not vLLM, and not szl-forge-lab.
    """
    return {
        "silhouette": "one OpenAI-shaped chat call, one pinned weight, one receipt",
        "atelier": atelier_lock(),
        "live": {
            "status": "MEASURED",
            "serve_studio": ATELIER_SERVE_STUDIO,
            "serve_studio_only": True,
            "owner": "FORGE (szl-holdings/szl-forge). KERNEL (this repo) pins + validates + receipts.",
            "not_this_repo": True,
            "not_forge_lab": True,
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
        "forge_lab": dict(FORGE_LAB_PIN),
        "energy_attested_runs": dict(ENERGY_ATTESTED_RUNS),
        "ask_and_act": dict(ASK_AND_ACT),
    }


def format_recipe() -> str:
    pin = weight_pin()
    sample = MEASURED_CPU_SAMPLE
    lines = [
        "szl-serve — canonical governed-inference recipe",
        "KERNEL-owned pin + validator + energy receipt. Not a vendor engine.",
        "Λ = Conjecture 1 (advisory). Doctrine v11 LOCKED 749/14/163.",
        "",
        "ATELIER LOCK",
        f"  serve studio : {ATELIER_SERVE_STUDIO} ONLY",
        f"  live CPU     : {LIVE_SPACE_BASE}",
        f"  model        : {KHIPU_OPENAI_MODEL_ID}",
        f"  {FORGE_LAB_SPACE} : SNAPSHOT, not a trainer, not a serve target",
        "  do not point szl-serve at forge-lab (no LIVE URL, curl, or model pin)",
        "  GPU           : ROADMAP",
        "  energy-attested-runs : 8/8 SIMULATED (not MEASURED NVML; not a live serve path)",
        "  Ask & Act     : NOT a live control plane",
        "",
        "WHAT THIS IS NOT",
        "  not vLLM, not TGI, not TensorRT-LLM, not SGLang, not Dynamo",
        "  not a tokens/s leaderboard, not proven trust, not a takeover of the HF Space",
        "  not szl-forge-lab (SNAPSHOT, not a trainer)",
        "  not Ask & Act as a live control plane",
        "  not energy-attested-runs as MEASURED serve energy",
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
        "ENERGY-ATTESTED-RUNS — 8/8 SIMULATED, not this recipe's CPU energy evidence",
        f"  space   : {ENERGY_ATTESTED_RUNS['space']}",
        f"  dataset : {ENERGY_ATTESTED_RUNS['dataset']}",
        f"  result  : {ENERGY_ATTESTED_RUNS['result']}  label={ENERGY_ATTESTED_RUNS['label']}",
        "  not MEASURED NVML joules; not a live serve path",
        "",
        "ASK & ACT — not a live control plane",
        "  a11oy operator tab (Operate / ask). Does not gate, launch, or control this recipe.",
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
    chat = openai_shaped_chat()
    return {
        "schema": "szl_serve/recipe@1",
        "atelier": atelier_lock(),
        "live_cpu": chat["live"],
        "airgap_twin": chat["airgap_twin"],
        "gpu": GPU_PATH,
        "forge_lab": dict(FORGE_LAB_PIN),
        "energy_attested_runs": dict(ENERGY_ATTESTED_RUNS),
        "ask_and_act": dict(ASK_AND_ACT),
        "weights": {k: v.to_dict() for k, v in WEIGHTS.items()},
        "lambda": "Conjecture 1 (advisory; never a theorem)",
        "doctrine": "v11 LOCKED 749/14/163",
    }
