# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Real offline distribution checks; no model, provider, GPU or network calls."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_MEMBER = "szl_serve/schemas/khipu.schema.json"
PIN_MEMBER = "szl_serve/schemas/PIN.json"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def build_wheel(source: Path, destination: Path, cwd: Path) -> Path:
    run([sys.executable, "-B", "-m", "pip", "--disable-pip-version-check", "wheel",
         "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir",
         str(destination), str(source)], cwd)
    wheels = list(destination.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


@pytest.fixture(scope="module")
def distributions(tmp_path_factory):
    workspace = tmp_path_factory.mktemp("szl-serve-wheel")
    source = workspace / "source"
    source.mkdir()
    for directory in ("szl_serve", "schemas"):
        shutil.copytree(ROOT / directory, source / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for filename in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(ROOT / filename, source / filename)
    wheel = build_wheel(source, workspace / "direct-wheel", workspace)
    sdists = workspace / "sdist"
    sdists.mkdir()
    run([sys.executable, "-B", "-c",
         "import sys;from setuptools.build_meta import build_sdist;build_sdist(sys.argv[1])",
         str(sdists)], source)
    archives = list(sdists.glob("*.tar.gz"))
    assert len(archives) == 1
    roundtrip = build_wheel(archives[0], workspace / "roundtrip-wheel", workspace)
    installed = workspace / "installed"
    run([sys.executable, "-B", "-m", "pip", "--disable-pip-version-check", "install",
         "--no-index", "--no-deps", "--target", str(installed), str(wheel)], workspace)
    return wheel, roundtrip, installed


def test_wheel_and_sdist_roundtrip_include_exact_canonical_resources(distributions):
    canonical_schema = (ROOT / "schemas" / "khipu.schema.json").read_bytes()
    canonical_pin = (ROOT / "schemas" / "PIN.json").read_bytes()
    pin = json.loads(canonical_pin)
    assert len(canonical_schema) == pin["bytes"] == 6262
    assert hashlib.sha256(canonical_schema).hexdigest() == pin["sha256"]
    for wheel in distributions[:2]:
        with zipfile.ZipFile(wheel) as archive:
            assert archive.read(SCHEMA_MEMBER) == canonical_schema
            assert archive.read(PIN_MEMBER) == canonical_pin


def test_installed_wheel_validates_benign_abstain_outside_checkout(
        distributions, tmp_path, plan_valid_abstain):
    installed = distributions[2]
    proposal = tmp_path / "benign-abstain.json"
    proposal.write_text(json.dumps(plan_valid_abstain), encoding="utf-8")
    probe = r'''
import hashlib, json, sys
from pathlib import Path
installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import szl_serve
from szl_serve.schema import schema_path, schema_sha256, validate_plan
assert Path(szl_serve.__file__).resolve().is_relative_to(installed)
assert schema_path().resolve() == installed / "szl_serve" / "schemas" / "khipu.schema.json"
pin = json.loads((schema_path().parent / "PIN.json").read_text(encoding="utf-8"))
assert len(schema_path().read_bytes()) == pin["bytes"] == 6262
assert schema_sha256() == pin["sha256"]
plan = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert plan["decision"] == "ABSTAIN"
result = validate_plan(plan, source="SYNTHETIC")
assert result.ok and result.disposition == "ACCEPT_PROPOSAL", result.reasons
assert result.brain_binding_status == "NOT_RESOLVED"
'''
    run([sys.executable, "-I", "-B", "-c", probe, str(installed), str(proposal)], tmp_path)


def test_tampered_packaged_schema_rejects_without_using_fallback(distributions, tmp_path):
    installed = tmp_path / "installed"
    shutil.copytree(distributions[2], installed)
    # A valid sibling copy cannot replace a corrupt preferred package resource.
    fallback = installed / "schemas"
    fallback.mkdir()
    shutil.copy2(ROOT / "schemas" / "khipu.schema.json", fallback / "khipu.schema.json")
    packaged = installed / "szl_serve" / "schemas" / "khipu.schema.json"
    packaged.write_bytes(packaged.read_bytes() + b"\n")
    probe = r'''
import sys
sys.path.insert(0, sys.argv[1])
from szl_serve.schema import load_khipu_schema
try:
    load_khipu_schema()
except RuntimeError as error:
    assert "pin mismatch" in str(error)
else:
    raise AssertionError("tampered package schema was accepted")
'''
    run([sys.executable, "-I", "-B", "-c", probe, str(installed)], tmp_path)
