# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Historical CPU recipe and migration to the governed A11oy Atelier form.

The public OpenAI chat route is RETIRED. Its dated measurement and immutable
artifact/source pins remain evidence, not current serving qualification.
This module prints navigation and contract metadata; it never sends a prompt,
forwards an obsolete request, or authorizes an action. Local engine commands
are unqualified recipes. The separate modelhost deployment owns its own gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import shlex

# ---------------------------------------------------------------------------
# Immutable historical artifact identity (Khipu GGUF Q4_K_M).
# ---------------------------------------------------------------------------
KHIPU_REPO = "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF"
KHIPU_REVISION = "67d60ec577730747055491640cfb91fc4a4b5d25"
KHIPU_FILENAME = "SZL-Khipu-1.5B-Q4_K_M.gguf"
KHIPU_LFS_SHA256 = "13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a"
KHIPU_BYTES = 986047904
KHIPU_QUANT = "Q4_K_M"
KHIPU_OPENAI_MODEL_ID = f"{KHIPU_REPO}@{KHIPU_REVISION}"

# Compatibility names for the historical CPU surface. LIVE_* is not a readiness
# claim: the chat route is retired, and only metadata GETs remain in qualification.
ATELIER_SERVE_STUDIO = "SZLHOLDINGS/szl-model-inference-lab"
LIVE_SPACE_ID = ATELIER_SERVE_STUDIO
LIVE_SPACE_URL = "https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab"
LIVE_SPACE_BASE = "https://szlholdings-szl-model-inference-lab.hf.space"
LIVE_CHAT_URL = f"{LIVE_SPACE_BASE}/v1/chat/completions"
LIVE_MODELS_URL = f"{LIVE_SPACE_BASE}/v1/models"
LIVE_CONTRACT_URL = f"{LIVE_SPACE_BASE}/.well-known/szl-inference-contract.json"
LIVE_IDENTITY_URL = f"{LIVE_SPACE_BASE}/api/v1/identity"
FORGE_SOURCE_REVISION = "e28abe9d4be3ce5efbb09ea2a3a248494c654636"
FORGE_SPACE_SOURCE = (
    "https://github.com/szl-holdings/szl-forge/tree/"
    f"{FORGE_SOURCE_REVISION}/spaces/szl-model-inference-lab"
)

LEGACY_RECIPE_STATE = "RETIRED"
ATELIER_FORM_PATH = "/command-centre#cpu-work"
ATELIER_TURN_PATH = "/api/a11oy/v1/atelier/cpu-lab/turn"


class RetiredRecipeError(RuntimeError):
    """The legacy executable recipe must not send or forward a request."""


def atelier_migration() -> Dict[str, Any]:
    """Describe the existing operator boundary, without creating an executor."""
    return {
        "availability": "NOT_PROBED",
        "deployment": "Your operator-managed A11oy deployment",
        "ui_path": ATELIER_FORM_PATH,
        "method": "POST",
        "api_path": ATELIER_TURN_PATH,
        "operator_authentication_required": True,
        "authorization_placeholder": "Bearer <A11OY_OPERATOR_TOKEN>",
        "public_share_acknowledged_required": True,
        "declared_required": "PUBLIC",
        "max_output_tokens": 32,
        "grounding_required": True,
        "expected_success_response": {
            "provider_decision": "PROPOSAL",
            "authority": "NO_ACTION_AUTHORITY",
            "executed": False,
            "provider_output_signature_status": "UNSIGNED_LOCAL",
        },
        "tool_authority": False,
        "action_authority": False,
        "automatic_forwarding": False,
        "note": (
            "Open the form on your verified A11oy origin. Confirm public disclosure "
            "for the specific prompt. The operator bearer belongs only to A11oy, "
            "never to the public lab. This package does not execute the request."
        ),
    }

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
    "legacy_route_state": LEGACY_RECIPE_STATE,
    "migration": atelier_migration(),
    "model": KHIPU_OPENAI_MODEL_ID,
    "forge_lab": FORGE_LAB_PIN,
    "energy_attested_runs": ENERGY_ATTESTED_RUNS,
    "ask_and_act": ASK_AND_ACT,
    "gpu": "ROADMAP",
}

# MEASURED sample (2026-11-04). Raw counts + elapsed. Not a tokens/s claim.
# Evidence: evidence/measured-cpu-serve-20261104.json (hash-chained UNSIGNED receipt).
MEASURED_CPU_SAMPLE: Dict[str, Any] = {
    "date": "2026-11-04",
    "stamp": "2026-11-04T17:46:48Z",
    "surface": LIVE_SPACE_BASE,
    "method": "POST /v1/chat/completions",
    "model": KHIPU_OPENAI_MODEL_ID,
    "completion_tokens": 24,
    "prompt_tokens": 49,
    "total_tokens": 73,
    "elapsed_ms": 8237,
    "execution_record": "UNSIGNED",
    "energy": {"joules": None, "label": "UNAVAILABLE"},
    "tokens_per_second": None,
    "gpu": "ROADMAP",
    "hardware": {
        "required": "cpu-basic",
        "accelerator_observed": "cpu",
        "cpu_cores_observed": "2",
        "memory_observed": "16.0G",
    },
    "evidence": "evidence/measured-cpu-serve-20261104.json",
    "chat_id": "chatcmpl-szl-406b010a26df4aa7a62913f8ab3d89e4",
    "request_sha256": "3ebaa71f2226218cc6d9b444ee8d0cb8e52a1d57e110c23d2a88460dca34c22d",
    "response_sha256": "2dc8910faef0fd417bdc5653bfe3bbcee9c7793b196c707ca8e780f934968d15",
    "note": (
        "MEASURED wall elapsed and tokenizer completion count from the FORGE "
        "Space on 2026-11-04 (cpu-basic). Not a tokens/s leaderboard. Not proven "
        "trust. Energy was not an NVML delta on that CPU box, so joules stay null "
        "/ UNAVAILABLE. GPU remains ROADMAP. Supersedes the 2026-08-28 sample "
        "(21 tokens / 2053 ms) as the CARD pin."
    ),
}

DEFAULT_WEIGHT_ID = "khipu"


@dataclass(frozen=True)
class WeightPin:
    weight_id: str
    status: str  # PINNED artifact identity | ROADMAP
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
        status="PINNED",
        repo_id=KHIPU_REPO,
        revision=KHIPU_REVISION,
        filename=KHIPU_FILENAME,
        lfs_sha256=KHIPU_LFS_SHA256,
        bytes=KHIPU_BYTES,
        quant=KHIPU_QUANT,
        openai_model_id=KHIPU_OPENAI_MODEL_ID,
        note=(
            "Immutable artifact identity from the historical CPU sample. "
            "The public OpenAI route is RETIRED. A pin does not qualify serving; "
            "schema validation stays outside these bytes."
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
    """Compatibility helper: no legacy serving target is currently qualified."""
    return ()


def is_forbidden_serve_target(value: str) -> bool:
    """True if a URL/id would point szl-serve at SNAPSHOT forge-lab."""
    return "szl-forge-lab" in value.lower()


def atelier_lock() -> Dict[str, Any]:
    """Historical lab identity plus the separate authenticated migration path."""
    return {
        "schema": "szl_serve/atelier_lock@1",
        "serve_studio": ATELIER_SERVE_STUDIO,
        "serve_studio_only": True,
        "live_cpu": LIVE_SPACE_BASE,
        "legacy_route_state": LEGACY_RECIPE_STATE,
        "migration": atelier_migration(),
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
    """Retained import with an explicit failure; never echo or forward the prompt."""
    raise RetiredRecipeError(
        "RETIRED: POST /v1/chat/completions returns 410. "
        f"Open {ATELIER_FORM_PATH} on your authenticated A11oy deployment; "
        "public disclosure requires acknowledgement for each prompt."
    )


def llama_cli_command(prompt: str = "Navigate: which receipt signed decision d-42?") -> str:
    """Return a POSIX-shell recipe with one literal prompt argument."""
    return (
        f"llama-cli -hf {KHIPU_REPO}:{KHIPU_QUANT} "
        f"-p {shlex.quote(prompt)}"
    )


def llama_server_command(host: str = "127.0.0.1", port: int = 8080) -> str:
    """Quote server values for a POSIX shell; the engine validates their meaning."""
    return (
        f"llama-server -hf {KHIPU_REPO}:{KHIPU_QUANT} "
        f"--host {shlex.quote(host)} --port {shlex.quote(str(port))}"
    )


def ollama_command() -> str:
    return f"ollama run hf.co/{KHIPU_REPO}:{KHIPU_QUANT}"


def openai_shaped_chat() -> Dict[str, Any]:
    """Compatibility metadata for a retired recipe; it contains no public curl."""
    return {
        "silhouette": "retired OpenAI recipe; navigate to governed A11oy Atelier",
        "atelier": atelier_lock(),
        "migration": atelier_migration(),
        "live": {
            "status": LEGACY_RECIPE_STATE,
            "available": False,
            "status_code": 410,
            "automatic_forwarding": False,
            "serve_studio": ATELIER_SERVE_STUDIO,
            "serve_studio_only": True,
            "owner": "FORGE (szl-holdings/szl-forge). KERNEL (this repo) pins + validates + receipts.",
            "not_this_repo": True,
            "not_forge_lab": True,
            "base_url": f"{LIVE_SPACE_BASE}/v1",
            "method": "POST",
            "path": "/v1/chat/completions",
            "model": KHIPU_OPENAI_MODEL_ID,
            "curl": None,
            "sample": MEASURED_CPU_SAMPLE,
            "space": LIVE_SPACE_URL,
            "contract": LIVE_CONTRACT_URL,
        },
        "airgap_twin": {
            "status": "UNQUALIFIED_RECIPE",
            "note": (
                "Local llama.cpp / Ollama command templates select a Hub quant label. "
                "Verify downloaded bytes against the immutable artifact pin before use. "
                "No current serving observation is made by this package."
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
        "szl-serve - historical evidence and governed Atelier migration",
        "KERNEL-owned pin + validator + energy receipt. Not a vendor engine.",
        "Lambda = Conjecture 1 (advisory). Doctrine v11 LOCKED 749/14/163.",
        "",
        "RETIRED PUBLIC OPENAI RECIPE",
        f"  historical lab : {LIVE_SPACE_BASE}",
        "  POST /v1/chat/completions : RETIRED (HTTP 410)",
        "  No executable public chat request; no automatic forwarding.",
        "",
        "A11OY ATELIER MIGRATION - availability NOT_PROBED",
        f"  open form : {ATELIER_FORM_PATH} on your verified A11oy deployment",
        f"  operator API : POST {ATELIER_TURN_PATH}",
        "  operator authentication is required; use the existing form",
        "  explicit fields : prompt, declared=PUBLIC, public_share_acknowledged=true",
        "  acknowledge public disclosure for the specific prompt before submission",
        "  max_output_tokens <= 32; grounding required; output remains a proposal",
        "  expected validated success: provider_decision=PROPOSAL, authority=NO_ACTION_AUTHORITY",
        "  expected validated success: executed=false, provider_output_signature_status=UNSIGNED_LOCAL",
        "  tool authority: none; action authority: none",
        "  Send the operator bearer only to A11oy, never to the public lab.",
        "  This package navigates and documents; it does not execute the request.",
        "  Contract details: https://github.com/szl-holdings/szl-serve/blob/main/docs/atelier-migration.md",
        "",
        "ATELIER LOCK - historical backend identity, not serving qualification",
        f"  pinned lab : {ATELIER_SERVE_STUDIO} ONLY",
        f"  {FORGE_LAB_SPACE} : SNAPSHOT, not a trainer, not a serve target",
        "  do not point szl-serve at forge-lab (no LIVE URL, curl, or model pin)",
        "  GPU           : ROADMAP (vendor-engine integrations)",
        "  energy-attested-runs : 8/8 SIMULATED (not MEASURED NVML; not a live serve path)",
        "  Ask & Act     : NOT a live control plane",
        "",
        "HISTORICAL CPU MEASUREMENT - not current availability",
        f"  source  : {FORGE_SPACE_SOURCE}",
        f"  forge   : {FORGE_SOURCE_REVISION} (historical source pin)",
        f"  model   : {pin.openai_model_id}",
        f"  GGUF    : {pin.filename}  sha256 {pin.lfs_sha256}  ({pin.bytes} bytes)",
        f"  sample  : {sample['date']}  completion_tokens={sample['completion_tokens']}  "
        f"elapsed_ms={sample['elapsed_ms']}  execution_record={sample['execution_record']}",
        "  energy  : joules=null  label=UNAVAILABLE (CPU; no NVML delta)",
        "  tokens/s: not claimed (raw counts + elapsed only)",
        "",
        "AIRGAP TWIN - unqualified local command templates, not a vLLM clone",
        "  Verify downloaded bytes against the artifact pin before use.",
        f"  {llama_cli_command()}",
        f"  {llama_server_command()}",
        f"  {ollama_command()}",
        "",
        "GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo: ROADMAP",
        "  GPU attention: ROADMAP (no fused/paged-attention LIVE claim; no tokens/s invented)",
        "  The separate deploy/modelhost service owns its own readiness gates.",
        "",
        "CONTROLLER",
        "  model output is proposal-only; validate against schemas/khipu.schema.json",
        "  hallucinated citedNodeIds -> REJECT (never repaired into a green plan)",
        "  brainBinding.status stays NOT_RESOLVED",
        "  real model provenance = MODEL_PROPOSED (not SYNTHETIC)",
        "  wrap energy: MEASURED NVML delta or UNAVAILABLE; receipt UNSIGNED unless a key exists",
    ]
    return "\n".join(lines) + "\n"


def recipe_document() -> Dict[str, Any]:
    chat = openai_shaped_chat()
    return {
        "schema": "szl_serve/recipe@2",
        "migration": atelier_migration(),
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
