# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""Execute generated recipes against argument recorders, never real engines."""
import json
import os
import shutil
import subprocess
import sys

import pytest

from szl_serve.recipe import live_openai_curl, llama_cli_command, llama_server_command


pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("sh") is None,
    reason="generated recipes target POSIX shells",
)


@pytest.fixture
def run_recipe(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("curl", "llama-cli", "llama-server"):
        executable = bin_dir / name
        executable.write_text(
            f"#!{sys.executable}\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        executable.chmod(0o700)

    def run(command):
        result = subprocess.run(
            [shutil.which("sh"), "-c", command],
            cwd=tmp_path,
            env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]},
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return json.loads(result.stdout)

    return run


@pytest.mark.parametrize("prompt", [
    "", "ordinary text", "it's quoted", "both ' and \" quotes",
    "$(printf expanded)", "`printf expanded`", "$HOME; & | > < * ?",
    "a\nb\t\\path", "Unicode: Λ café",
    "it's $(touch should-not-exist) and `touch also-must-not-exist`",
])
def test_prompt_is_one_literal_argument(run_recipe, tmp_path, prompt):
    args = run_recipe(live_openai_curl(prompt))
    payload = json.loads(args[args.index("-d") + 1])
    assert payload["messages"][0]["content"] == prompt
    assert len(args) == 7

    args = run_recipe(llama_cli_command(prompt))
    assert args[args.index("-p") + 1] == prompt
    assert len(args) == 4
    assert not (tmp_path / "should-not-exist").exists()
    assert not (tmp_path / "also-must-not-exist").exists()


@pytest.mark.parametrize("host,port", [
    ("127.0.0.1", 8080),
    ("::1", 8080),
    ("$(printf injected)", "8080; printf injected"),
    ("host name 'quoted'", "8080\nother"),
])
def test_server_values_cannot_become_shell_syntax(run_recipe, host, port):
    args = run_recipe(llama_server_command(host, port))
    assert args[args.index("--host") + 1] == host
    assert args[args.index("--port") + 1] == str(port)
    assert len(args) == 6
