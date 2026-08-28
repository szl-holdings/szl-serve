# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Recipe pins the MEASURED Space. No second runtime. No network."""
from __future__ import annotations

import json

from szl_serve.cli import main
from szl_serve.recipe import (
    ASK_AND_ACT,
    ATELIER_LOCK,
    ATELIER_SERVE_STUDIO,
    ENERGY_ATTESTED_RUNS,
    FORGE_LAB_PIN,
    FORGE_LAB_SPACE,
    GPU_PATH,
    KHIPU_LFS_SHA256,
    KHIPU_OPENAI_MODEL_ID,
    LIVE_CHAT_URL,
    LIVE_SPACE_BASE,
    MEASURED_CPU_SAMPLE,
    WEIGHTS,
    atelier_lock,
    format_recipe,
    is_forbidden_serve_target,
    llama_cli_command,
    llama_server_command,
    live_openai_curl,
    live_serve_targets,
    ollama_command,
    openai_shaped_chat,
    recipe_document,
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


def test_atelier_serve_studio_is_inference_lab_only():
    lock = atelier_lock()
    assert lock["serve_studio"] == "SZLHOLDINGS/szl-model-inference-lab"
    assert lock["serve_studio_only"] is True
    assert lock["live_cpu"] == "https://szlholdings-szl-model-inference-lab.hf.space"
    assert lock["model"] == KHIPU_OPENAI_MODEL_ID
    assert ATELIER_SERVE_STUDIO == LIVE_SPACE_BASE.replace(
        "https://szlholdings-", "SZLHOLDINGS/"
    ).replace(".hf.space", "")
    assert ATELIER_LOCK["serve_studio"] == ATELIER_SERVE_STUDIO
    doc = recipe_document()
    assert doc["atelier"]["serve_studio"] == ATELIER_SERVE_STUDIO
    assert doc["live_cpu"]["serve_studio"] == ATELIER_SERVE_STUDIO
    text = format_recipe()
    assert "ATELIER LOCK" in text
    assert "szl-model-inference-lab ONLY" in text
    assert LIVE_SPACE_BASE in text
    assert KHIPU_OPENAI_MODEL_ID in text


def test_forge_lab_is_snapshot_not_a_serve_target():
    pin = FORGE_LAB_PIN
    assert pin["id"] == "SZLHOLDINGS/szl-forge-lab"
    assert pin["class"] == "SNAPSHOT"
    assert pin["not_a_trainer"] is True
    assert pin["not_a_serve_target"] is True
    assert pin["curriculum"] == "BLUEPRINT_NOT_TRAINED"
    assert FORGE_LAB_SPACE == "SZLHOLDINGS/szl-forge-lab"

    live = openai_shaped_chat()["live"]
    live_blob = json.dumps(live)
    assert "szl-forge-lab" not in live_blob
    assert "szl-forge-lab" not in live["curl"]
    assert "szl-forge-lab" not in live["space"]
    assert "szl-forge-lab" not in live["base_url"]
    assert not is_forbidden_serve_target(LIVE_SPACE_BASE)
    assert not is_forbidden_serve_target(LIVE_CHAT_URL)
    assert not any(is_forbidden_serve_target(t) for t in live_serve_targets())
    assert is_forbidden_serve_target(FORGE_LAB_SPACE)
    assert is_forbidden_serve_target("https://huggingface.co/spaces/SZLHOLDINGS/szl-forge-lab")

    text = format_recipe()
    # Mentioned only as SNAPSHOT / not a trainer / not a serve target.
    assert "szl-forge-lab" in text
    assert "SNAPSHOT, not a trainer, not a serve target" in text
    assert "do not point szl-serve at forge-lab" in text
    # The curl block must still hit inference-lab only.
    assert "curl https://szlholdings-szl-model-inference-lab.hf.space/v1/chat/completions" in text
    assert "szlholdings-szl-forge-lab.hf.space" not in text
    assert "szlholdings-szl-forge-lab.hf.space" not in live_openai_curl()


def test_energy_attested_runs_are_simulated_not_measured_serve_energy():
    ear = ENERGY_ATTESTED_RUNS
    assert ear["id"] == "SZLHOLDINGS/energy-attested-runs"
    assert ear["result"] == "8/8"
    assert ear["label"] == "SIMULATED"
    assert ear["not_measured_nvml"] is True
    assert ear["not_a_live_serve_path"] is True
    doc = recipe_document()
    assert doc["energy_attested_runs"]["label"] == "SIMULATED"
    assert doc["energy_attested_runs"]["result"] == "8/8"
    text = format_recipe()
    assert "8/8 SIMULATED" in text
    assert "energy-attested-runs" in text
    # CPU sample energy stays UNAVAILABLE; SIMULATED corpus is not that evidence.
    assert MEASURED_CPU_SAMPLE["energy"]["label"] == "UNAVAILABLE"
    assert MEASURED_CPU_SAMPLE["energy"]["joules"] is None


def test_ask_and_act_is_not_a_live_control_plane():
    assert ASK_AND_ACT["status"] == "NOT_A_LIVE_CONTROL_PLANE"
    doc = recipe_document()
    assert doc["ask_and_act"]["status"] == "NOT_A_LIVE_CONTROL_PLANE"
    text = format_recipe()
    assert "Ask & Act" in text
    assert "not a live control plane" in text.lower() or "NOT a live control plane" in text


def test_gpu_remains_roadmap_in_atelier_lock():
    lock = atelier_lock()
    assert lock["gpu"]["status"] == "ROADMAP"
    assert GPU_PATH["status"] == "ROADMAP"
    text = format_recipe()
    assert "GPU           : ROADMAP" in text or "GPU / vLLM" in text
    assert "GPU attention: ROADMAP" in text


def test_cli_recipe_prints_atelier_lock(capsys):
    assert main(["recipe"]) == 0
    out = capsys.readouterr().out
    assert "ATELIER LOCK" in out
    assert "SZLHOLDINGS/szl-model-inference-lab ONLY" in out
    assert KHIPU_OPENAI_MODEL_ID in out
    assert "8/8 SIMULATED" in out
    assert "not a live control plane" in out.lower() or "NOT a live control plane" in out
    assert "szl-forge-lab" in out
    assert "SNAPSHOT" in out
    assert "szlholdings-szl-forge-lab.hf.space" not in out
