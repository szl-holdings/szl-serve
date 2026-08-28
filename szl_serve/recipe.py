# SPDX-License-Identifier: Apache-2.0
from .pins import GGUF_REPO, LIVE_LAB, MODEL_ID, GPU_ATTENTION

def llama_cpp_cmd() -> str:
    return f"llama-cli -hf {GGUF_REPO}:Q4_K_M -p 'Navigate: which receipt signed decision d-42?'"

def ollama_cmd() -> str:
    return f"ollama run hf.co/{GGUF_REPO}:Q4_K_M"

def recipe() -> dict:
    return {
        "live_lab": LIVE_LAB,
        "model_id": MODEL_ID,
        "cpu": {"llama.cpp": llama_cpp_cmd(), "ollama": ollama_cmd()},
        "gpu_attention": GPU_ATTENTION,
        "energy": "MEASURED NVML delta or UNAVAILABLE; never fabricated",
        "lambda": "Conjecture 1",
        "note": "Forge Space is the bounded demo; this repo is the KERNEL recipe + validator",
    }
