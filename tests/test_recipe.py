# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Recipe pins the MEASURED Space. No second runtime. No network."""
from __future__ import annotations

from szl_serve.cli import main
from szl_serve.recipe import (
    GPU_PATH,
    KHIPU_LFS_SHA256,
    KHIPU_OPENAI_MODEL_ID,
    LIVE_CHAT_URL,
    LIVE_SPACE_BASE,
    MEASURED_CPU_SAMPLE,
    WEIGHTS,
    format_recipe,
    llama_cli_command,
    llama_server_command,
    ollama_command,
    openai_shaped_chat,
)


def test_live_cpu_is_the_existing_space_not_a_second_runtime():
    chat = openai_shaped_chat()
    live = chat["live"]
    assert live["status"] == "MEASURED"
    assert live["not_this_repo"] is True
    assert live["path"] == "/v1/chat/completions"
    assert live["method"] == "POST"
    assert live["model"] == KHIPU_OPENAI_MODEL_ID
    assert live["model"].endswith("@67d60ec577730747055491640cfb91fc4a4b5d25")
    assert LIVE_SPACE_BASE == "https://szlholdings-szl-model-inference-lab.hf.space"
    assert LIVE_CHAT_URL.endswith("/v1/chat/completions")
    assert "szl-model-inference-lab" in live["space"]
    assert live["curl"].startswith("curl https://szlholdings-szl-model-inference-lab.hf.space/v1/chat/completions")


def test_measured_sample_is_raw_counts_not_tokens_per_second():
    sample = MEASURED_CPU_SAMPLE
    assert sample["date"] == "2026-08-28"
    assert sample["completion_tokens"] == 21
    assert sample["elapsed_ms"] == 2053
    assert sample["execution_record"] == "UNSIGNED"
    assert sample["tokens_per_second"] is None
    assert sample["energy"]["joules"] is None
    assert sample["energy"]["label"] == "UNAVAILABLE"


def test_gpu_vllm_tgi_remain_roadmap():
    assert GPU_PATH["status"] == "ROADMAP"
    assert "vLLM" in GPU_PATH["engines"]
    assert "TGI" in GPU_PATH["engines"]
    assert GPU_PATH["tokens_per_second"] is None
    assert GPU_PATH["joules"] is None
    assert GPU_PATH["attention"]["status"] == "ROADMAP"
    assert GPU_PATH["attention"]["tokens_per_second"] is None


def test_chaski_and_receiptagent_are_roadmap_stubs():
    assert WEIGHTS["khipu"].status == "LIVE"
    assert WEIGHTS["khipu"].lfs_sha256 == KHIPU_LFS_SHA256
    assert WEIGHTS["khipu"].bytes == 986047904
    assert WEIGHTS["chaski"].status == "ROADMAP"
    assert WEIGHTS["chaski"].lfs_sha256 is None
    assert WEIGHTS["receiptagent"].status == "ROADMAP"
    assert WEIGHTS["receiptagent"].repo_id is None


def test_airgap_twin_is_llamacpp_ollama_not_vllm():
    twin = openai_shaped_chat()["airgap_twin"]
    assert "vLLM" not in twin["llama_cli"]
    assert "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M" in llama_cli_command()
    assert "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M" in llama_server_command()
    assert "hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M" in ollama_command()
    text = format_recipe()
    assert "AIRGAP TWIN" in text
    assert "not a vLLM clone" in text
    assert "do not invent a second runtime" in text
    assert "POST /v1/chat/completions" in text


def test_cli_recipe_prints_space_and_airgap(capsys):
    assert main(["recipe"]) == 0
    out = capsys.readouterr().out
    assert LIVE_SPACE_BASE in out
    assert KHIPU_OPENAI_MODEL_ID in out
    assert "llama-cli" in out
    assert "ollama run" in out
    assert "GPU attention: ROADMAP" in out


def test_cli_validate_rejects_hallucination(capsys):
    code = main(["validate", "tests/fixtures/plan_hallucinated_cited.json"])
    captured = capsys.readouterr()
    assert code == 1
    assert "REJECT" in captured.out or "REJECT" in captured.err
