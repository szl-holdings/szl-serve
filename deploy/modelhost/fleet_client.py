#!/usr/bin/env python3
"""Operate the model fleet over an existing, verified SSH connection.

Examples (Paramiko must already be installed):
    python fleet_client.py inventory --host gate1
    python fleet_client.py generate --host cuda --model MODEL_NAME \
        --prompt-file prompt.txt --max-new-tokens 64

Hosts are fixed, gate1 is the default, and requests are never retried or moved
to another host. Prompts travel as JSON on SSH stdin, never in a shell command.
The remote helper uses loopback HTTP and the host's optional origin credential.
"""
from __future__ import annotations

import argparse
import hmac
import json
from pathlib import Path
import re
import shlex
import sys

HOSTS = {"gate1": ("64.247.196.50", 8090), "cuda": ("64.247.206.118", 8091)}
MAX_PROMPT_CHARS = 16384
MAX_BODY_BYTES = 65536
MAX_NEW_TOKENS = 256
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
ALLOWED_REQUESTS = {("GET", "/models"), ("GET", "/ready"), ("POST", "/generate")}

# This command is constant. No prompt, model, credential, path, or other caller
# input is interpolated into Python source or into the SSH shell command.
REMOTE_PROGRAM = r'''
import json, sys, urllib.request, urllib.error
from pathlib import Path

MAX_RESPONSE = 4 * 1024 * 1024

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def run():
    raw = sys.stdin.buffer.read(262145)
    if len(raw) > 262144:
        raise ValueError("input_limit")
    envelope = json.loads(raw)
    port, method, path = envelope["port"], envelope["method"], envelope["path"]
    if type(port) is not int or port not in (8090, 8091):
        raise ValueError("invalid_port")
    if (method, path) not in {("GET", "/models"), ("GET", "/ready"), ("POST", "/generate")}:
        raise ValueError("invalid_request")
    headers = {"Accept": "application/json"}
    # Read the same private configuration as the deployed v2 systemd service.
    # The untouched legacy root configuration is retained only for recovery.
    config_path = Path("/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/host_config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    token = config.get("origin_auth_token")
    token_file = config.get("origin_auth_token_file")
    if token_file:
        token_path = Path(token_file)
        if not token_path.is_absolute():
            token_path = config_path.parent / token_path
        token = token_path.read_text(encoding="utf-8").strip()
    if token is not None:
        if not isinstance(token, str) or not token or "\r" in token or "\n" in token:
            raise ValueError("invalid_origin_auth")
        headers["Authorization"] = "Bearer " + token
    body = None
    if method == "POST":
        body = json.dumps(envelope["payload"], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(body) > 65536:
            raise ValueError("body_limit")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=body, headers=headers, method=method)
    # Ignore ambient proxy settings and refuse redirects, keeping credentials
    # and prompts confined to the selected host's loopback service.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=75)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        status = response.code
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("response_limit")
    return {"status": status, "body": json.loads(raw)}

try:
    result = run()
except Exception:
    # Never echo input, config, origin credentials, or exception text.
    print(json.dumps({"status": 0, "error": "remote_request_failed"}))
    sys.exit(1)
print(json.dumps(result, ensure_ascii=True, allow_nan=False))
'''
REMOTE_COMMAND = "python3 -B -c " + shlex.quote(REMOTE_PROGRAM)


class ClientError(Exception):
    """A safe, machine-readable error code without request or secret contents."""


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def build_generation_payload(catalog, model, prompt, max_new_tokens=MAX_NEW_TOKENS):
    if (not isinstance(model, str) or not model.strip() or model != model.strip()
            or len(model) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in model)):
        raise ClientError("invalid_model")
    if not isinstance(prompt, str) or len(prompt) > MAX_PROMPT_CHARS:
        raise ClientError("invalid_or_oversized_prompt")
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= MAX_NEW_TOKENS:
        raise ClientError("invalid_max_new_tokens")
    models = catalog.get("models", {}) if isinstance(catalog, dict) else {}
    row = models.get(model) if isinstance(models, dict) else None
    if not isinstance(row, dict):
        raise ClientError("model_not_in_selected_host_catalog")
    if row.get("status") != "loaded" or row.get("identity_verified") is not True:
        raise ClientError("model_identity_not_ready")
    fingerprint = row.get("artifact_fingerprint")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise ClientError("invalid_catalog_fingerprint")
    payload = {"model": model, "prompt": prompt, "max_new_tokens": max_new_tokens,
               "expected_artifact_fingerprint": fingerprint}
    if len(json_bytes(payload)) > MAX_BODY_BYTES:
        raise ClientError("request_body_too_large")
    return payload


def verify_generation_response(payload, response):
    if (not isinstance(response, dict) or response.get("model") != payload["model"]
            or not isinstance(response.get("artifact_fingerprint"), str)
            or re.fullmatch(r"[0-9a-f]{64}", response["artifact_fingerprint"]) is None
            or not hmac.compare_digest(response["artifact_fingerprint"], payload["expected_artifact_fingerprint"])):
        raise ClientError("response_identity_mismatch")


def encode_envelope(host, method, path, payload=None):
    if host not in HOSTS or (method, path) not in ALLOWED_REQUESTS:
        raise ClientError("invalid_host_or_endpoint")
    envelope = {"port": HOSTS[host][1], "method": method, "path": path}
    if method == "POST":
        if not isinstance(payload, dict) or len(json_bytes(payload)) > MAX_BODY_BYTES:
            raise ClientError("invalid_request_body")
        envelope["payload"] = payload
    elif payload is not None:
        raise ClientError("unexpected_request_body")
    return json_bytes(envelope)


def read_prompt(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        raise ClientError("prompt_file_too_large")
    try:
        prompt = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ClientError("prompt_file_must_be_utf8") from None
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ClientError("invalid_or_oversized_prompt")
    return prompt


class FleetSession:
    def __init__(self, host, key_file, known_hosts=None):
        if host not in HOSTS:
            raise ClientError("invalid_host")
        try:
            import paramiko
        except ImportError:
            raise ClientError("paramiko_is_required") from None
        self.host = host
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        if known_hosts:
            self.client.load_host_keys(str(Path(known_hosts).expanduser()))
        self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            self.client.connect(HOSTS[host][0], username="Ubuntu",
                key_filename=str(Path(key_file).expanduser()), timeout=15,
                banner_timeout=15, auth_timeout=15, look_for_keys=False, allow_agent=False)
        except Exception:
            self.client.close()
            raise ClientError("ssh_connection_failed_check_key_and_known_hosts") from None

    def close(self):
        self.client.close()

    def request(self, method, path, payload=None):
        encoded = encode_envelope(self.host, method, path, payload)
        channel = None
        try:
            stdin, stdout, stderr = self.client.exec_command(REMOTE_COMMAND, timeout=100)
            channel = stdout.channel
            stdin.write(encoded)
            stdin.flush()
            stdin.channel.shutdown_write()
            raw = stdout.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ClientError("remote_response_too_large")
            stderr.read(4096)  # Discard remote diagnostics; they must not leak credentials.
            exit_status = channel.recv_exit_status()
            response = json.loads(raw)
            if exit_status != 0 or not isinstance(response, dict) or type(response.get("status")) is not int:
                raise ClientError("remote_request_failed")
            return response
        except ClientError:
            raise
        except Exception:
            raise ClientError("ssh_request_failed_no_retry_attempted") from None
        finally:
            if channel is not None:
                channel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "generate"):
        command = commands.add_parser(name)
        command.add_argument("--host", choices=HOSTS, default="gate1")
        command.add_argument("--key-file", type=Path,
                             default=Path.home() / ".ssh" / "szl_massed_a6000_ed25519")
        command.add_argument("--known-hosts", type=Path,
                             help="Existing trusted known_hosts file; unknown hosts are rejected")
        if name == "generate":
            command.add_argument("--model", required=True)
            command.add_argument("--prompt-file", type=Path, required=True)
            command.add_argument("--max-new-tokens", type=int, choices=range(1, 257), default=256,
                                 metavar="1..256")
    args = parser.parse_args(argv)
    session = None
    try:
        prompt = read_prompt(args.prompt_file) if args.command == "generate" else None
        session = FleetSession(args.host, args.key_file, args.known_hosts)
        catalog = session.request("GET", "/models")
        if args.command == "inventory":
            ready = session.request("GET", "/ready")
            print(json.dumps({"host": args.host, "transport": "ssh_loopback", "models": catalog,
                              "ready": ready}, indent=2, ensure_ascii=False))
            return 0 if catalog["status"] == ready["status"] == 200 else 2
        if catalog["status"] != 200:
            raise ClientError("catalog_unavailable")
        payload = build_generation_payload(catalog.get("body"), args.model, prompt, args.max_new_tokens)
        response = session.request("POST", "/generate", payload)
        if response["status"] == 200:
            verify_generation_response(payload, response.get("body"))
        print(json.dumps({"host": args.host, "status": response["status"],
                          "result": response.get("body")}, indent=2, ensure_ascii=False))
        return 0 if response["status"] == 200 else 2
    except ClientError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    except OSError:
        print(json.dumps({"error": "local_file_unavailable"}), file=sys.stderr)
        return 2
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
