# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""The retired public recipe cannot execute or claim current serving readiness."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

import pytest

from szl_serve.cli import main
from szl_serve.recipe import (
    ASK_AND_ACT,
    ATELIER_LOCK,
    ATELIER_FORM_PATH,
    ATELIER_TURN_PATH,
    ATELIER_SERVE_STUDIO,
    ENERGY_ATTESTED_RUNS,
    FORGE_LAB_PIN,
    FORGE_LAB_SPACE,
    FORGE_SOURCE_REVISION,
    FORGE_SPACE_SOURCE,
    GPU_PATH,
    KHIPU_LFS_SHA256,
    KHIPU_OPENAI_MODEL_ID,
    LIVE_CHAT_URL,
    LIVE_SPACE_BASE,
    MEASURED_CPU_SAMPLE,
    RetiredRecipeError,
    WEIGHTS,
    atelier_lock,
    atelier_migration,
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


def test_legacy_metadata_preserves_identity_without_executable_recipe():
    chat = openai_shaped_chat()
    live = chat["live"]
    assert live["status"] == "RETIRED"
    assert live["available"] is False
    assert live["status_code"] == 410
    assert live["automatic_forwarding"] is False
    assert live["not_this_repo"] is True
    assert live["path"] == "/v1/chat/completions"
    assert live["method"] == "POST"
    assert live["model"] == KHIPU_OPENAI_MODEL_ID
    assert live["model"].endswith("@67d60ec577730747055491640cfb91fc4a4b5d25")
    assert LIVE_SPACE_BASE == "https://szlholdings-szl-model-inference-lab.hf.space"
    assert LIVE_CHAT_URL.endswith("/v1/chat/completions")
    assert "szl-model-inference-lab" in live["space"]
    assert live["curl"] is None
    assert live_serve_targets() == ()
    assert FORGE_SOURCE_REVISION == "e28abe9d4be3ce5efbb09ea2a3a248494c654636"
    assert FORGE_SOURCE_REVISION in FORGE_SPACE_SOURCE
    assert "/tree/main/" not in FORGE_SPACE_SOURCE
    document = recipe_document()
    assert document["schema"] == "szl_serve/recipe@2"
    assert document["live_cpu"]["status"] == "RETIRED"


@pytest.mark.parametrize("prompt", [
    "PRIVATE_PROMPT_SENTINEL",
    "PROMPT_SENTINEL'; $(touch should-not-exist); `id`",
    "PROMPT_SENTINEL\\nNEXT_LINE",
])
def test_deprecated_curl_fails_without_forwarding_or_echoing_prompt(prompt, monkeypatch, capsys):
    def prohibited(*_args, **_kwargs):
        pytest.fail("retired recipe must not perform network or process work")

    monkeypatch.setattr(socket, "create_connection", prohibited)
    monkeypatch.setattr(urllib.request, "urlopen", prohibited)
    monkeypatch.setattr(subprocess, "run", prohibited)
    with pytest.raises(RetiredRecipeError, match="RETIRED") as error:
        live_openai_curl(prompt)
    assert prompt not in str(error.value)
    assert ATELIER_FORM_PATH in str(error.value)
    assert capsys.readouterr().out == ""


def test_migration_describes_operator_public_disclosure_and_proposal_boundary():
    migration = atelier_migration()
    assert migration["availability"] == "NOT_PROBED"
    assert migration["ui_path"] == "/command-centre#cpu-work"
    assert migration["api_path"] == "/api/a11oy/v1/atelier/cpu-lab/turn"
    assert migration["method"] == "POST"
    assert migration["operator_authentication_required"] is True
    assert migration["authorization_placeholder"] == "Bearer <A11OY_OPERATOR_TOKEN>"
    assert migration["public_share_acknowledged_required"] is True
    assert migration["declared_required"] == "PUBLIC"
    assert migration["max_output_tokens"] == 32
    assert migration["grounding_required"] is True
    assert migration["expected_success_response"] == {
        "provider_decision": "PROPOSAL",
        "authority": "NO_ACTION_AUTHORITY",
        "executed": False,
        "provider_output_signature_status": "UNSIGNED_LOCAL",
    }
    assert migration["tool_authority"] is False
    assert migration["action_authority"] is False
    assert migration["automatic_forwarding"] is False


def test_default_recipe_is_navigation_only_without_network_or_execution(monkeypatch, capsys):
    def prohibited(*_args, **_kwargs):
        pytest.fail("printing the recipe must not qualify, execute, or contact a provider")

    monkeypatch.setattr(socket, "create_connection", prohibited)
    monkeypatch.setattr(urllib.request, "urlopen", prohibited)
    monkeypatch.setattr(subprocess, "run", prohibited)
    monkeypatch.setattr("szl_serve.cli.qualify", prohibited)
    assert main(["recipe"]) == 0
    output = capsys.readouterr().out
    assert "RETIRED PUBLIC OPENAI RECIPE" in output
    assert ATELIER_FORM_PATH in output
    assert ATELIER_TURN_PATH in output
    assert "public_share_acknowledged=true" in output
    assert "expected validated success: provider_decision=PROPOSAL, authority=NO_ACTION_AUTHORITY" in output
    assert "LIVE CPU (MEASURED)" not in output
    assert not any(line.lstrip().startswith("curl ") for line in output.splitlines())


def test_public_documentation_has_no_executable_legacy_request():
    root = Path(__file__).resolve().parents[1]
    for name in ["README.md", "CARD.md", "docs/atelier-migration.md"]:
        text = (root / name).read_text(encoding="utf-8")
        assert "RETIRED" in text
        assert "curl " + LIVE_CHAT_URL not in text
    migration = (root / "docs/atelier-migration.md").read_text(encoding="utf-8")
    assert '"public_share_acknowledged": true' in migration
    assert '"declared": "PUBLIC"' in migration
    assert "Bearer <A11OY_OPERATOR_TOKEN>" in migration


@pytest.mark.parametrize("identity,route,exit_code", [
    ("OBSERVED", "RETIRED", 2),
    ("DIVERGENT", "RETIRED", 2),
    ("UNKNOWN", "CONFLICT", 2),
    ("UNKNOWN", "UNKNOWN", 1),
    ("DIVERGENT", "DECLARED", 1),
    ("OBSERVED", "UNKNOWN", 1),
    ("OBSERVED", "DECLARED", 0),
])
def test_cli_qualification_keeps_route_exit_separate_from_identity(
        monkeypatch, capsys, identity, route, exit_code):
    payload = {
        "state": identity,
        "legacy_route": {"state": route},
        "serving_ready": False,
        "serving_state": "NOT_QUALIFIED",
    }
    monkeypatch.setattr("szl_serve.cli.qualify", lambda *_args, **_kwargs: payload)
    assert main(["qualify", "--output", "-"]) == exit_code
    emitted = json.loads(capsys.readouterr().out)
    assert emitted == payload
    assert emitted["serving_ready"] is False


def test_measured_sample_is_raw_counts_not_tokens_per_second():
    sample = MEASURED_CPU_SAMPLE
    assert sample["date"] == "2026-11-04"
    assert sample["completion_tokens"] == 24
    assert sample["elapsed_ms"] == 8237
    assert sample["execution_record"] == "UNSIGNED"
    assert sample["tokens_per_second"] is None
    assert sample["gpu"] == "ROADMAP"
    assert sample["energy"]["joules"] is None
    assert sample["energy"]["label"] == "UNAVAILABLE"
    assert sample["evidence"] == "evidence/measured-cpu-serve-20261104.json"
    assert sample["hardware"]["accelerator_observed"] == "cpu"


def test_gpu_vllm_tgi_remain_roadmap():
    assert GPU_PATH["status"] == "ROADMAP"
    assert "vLLM" in GPU_PATH["engines"]
    assert "TGI" in GPU_PATH["engines"]
    assert GPU_PATH["tokens_per_second"] is None
    assert GPU_PATH["joules"] is None
    assert GPU_PATH["attention"]["status"] == "ROADMAP"
    assert GPU_PATH["attention"]["tokens_per_second"] is None


def test_chaski_and_receiptagent_are_roadmap_stubs():
    assert WEIGHTS["khipu"].status == "PINNED"
    assert WEIGHTS["khipu"].lfs_sha256 == KHIPU_LFS_SHA256
    assert WEIGHTS["khipu"].bytes == 986047904
    assert WEIGHTS["chaski"].status == "ROADMAP"
    assert WEIGHTS["chaski"].lfs_sha256 is None
    assert WEIGHTS["receiptagent"].status == "ROADMAP"
    assert WEIGHTS["receiptagent"].repo_id is None


def test_airgap_twin_is_llamacpp_ollama_not_vllm():
    twin = openai_shaped_chat()["airgap_twin"]
    assert twin["status"] == "UNQUALIFIED_RECIPE"
    assert "vLLM" not in twin["llama_cli"]
    assert "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M" in llama_cli_command()
    assert "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M" in llama_server_command()
    assert "hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M" in ollama_command()
    text = format_recipe()
    assert "AIRGAP TWIN" in text
    assert "not a vLLM clone" in text
    assert "POST /v1/chat/completions" in text
    assert "RETIRED (HTTP 410)" in text


def test_cli_recipe_prints_historical_identity_and_local_template_boundary(capsys):
    assert main(["recipe"]) == 0
    out = capsys.readouterr().out
    assert LIVE_SPACE_BASE in out
    assert KHIPU_OPENAI_MODEL_ID in out
    assert "llama-cli" in out
    assert "ollama run" in out
    assert "unqualified local command templates" in out
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
    assert lock["legacy_route_state"] == "RETIRED"
    assert lock["migration"]["availability"] == "NOT_PROBED"
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
    assert live["curl"] is None
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
    # Navigation cannot create a new public inference path.
    assert "curl " + LIVE_CHAT_URL not in text
    assert "szlholdings-szl-forge-lab.hf.space" not in text
    assert live_serve_targets() == ()


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


def test_cli_recipe_subprocess_uses_portable_console_text():
    child_environment = os.environ.copy()
    child_environment["PYTHONIOENCODING"] = "cp1252"
    result = subprocess.run(
        [sys.executable, "-m", "szl_serve", "recipe"],
        cwd=Path(__file__).resolve().parents[1],
        env=child_environment,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("cp1252", errors="replace")
    output = result.stdout.decode("cp1252")
    assert output.isascii()
    assert "RETIRED PUBLIC OPENAI RECIPE" in output
    assert "/command-centre#cpu-work" in output
    assert "/api/a11oy/v1/atelier/cpu-lab/turn" in output
    assert "Lambda = Conjecture 1 (advisory)" in output
    assert "NO_ACTION_AUTHORITY" in output
