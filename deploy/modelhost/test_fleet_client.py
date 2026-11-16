import io
import json
from pathlib import Path
import tempfile
import unittest

from fleet_client import (ClientError, FleetSession, HOSTS, MAX_PROMPT_CHARS,
                          REMOTE_COMMAND, REMOTE_PROGRAM, build_generation_payload,
                          encode_envelope, read_prompt, verify_generation_response)


class FleetClientTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "a" * 64
        self.catalog = {"models": {"model.a": {"status": "loaded", "identity_verified": True,
                                             "artifact_fingerprint": self.fingerprint}}}

    def test_payload_pins_exact_catalog_identity(self):
        payload = build_generation_payload(self.catalog, "model.a", "hello", 17)
        self.assertEqual(payload, {"model": "model.a", "prompt": "hello", "max_new_tokens": 17,
                                   "expected_artifact_fingerprint": self.fingerprint})

    def test_prompt_limit_and_utf8_body_limit_are_not_truncated(self):
        payload = build_generation_payload(self.catalog, "model.a", "x" * MAX_PROMPT_CHARS)
        self.assertEqual(len(payload["prompt"]), MAX_PROMPT_CHARS)
        for prompt in ("x" * (MAX_PROMPT_CHARS + 1), "\U0001f30d" * MAX_PROMPT_CHARS, None):
            with self.subTest(prompt_type=type(prompt).__name__), self.assertRaises(ClientError):
                build_generation_payload(self.catalog, "model.a", prompt)

    def test_generation_limits_reject_coercions(self):
        for count in (0, 257, -1, True, 1.0, "12"):
            with self.subTest(count=count), self.assertRaises(ClientError):
                build_generation_payload(self.catalog, "model.a", "hello", count)

    def test_unverified_missing_and_malformed_catalog_entries_fail_closed(self):
        for catalog in ({}, {"models": []}, {"models": {"model.a": {"status": "pending"}}},
                        {"models": {"model.a": {"status": "loaded", "identity_verified": True,
                                                 "artifact_fingerprint": "bad"}}}):
            with self.subTest(catalog=catalog), self.assertRaises(ClientError):
                build_generation_payload(catalog, "model.a", "hello")

    def test_model_names_are_not_coerced_or_trimmed(self):
        for name in ("", " model.a", "model.a\n", "x" * 257, None):
            with self.subTest(name=name), self.assertRaises(ClientError):
                build_generation_payload(self.catalog, name, "hello")

    def test_shell_metacharacters_travel_only_as_json_stdin(self):
        prompt = "'; $(touch /tmp/do-not-execute) `whoami` \\ \n\U0001f30d"
        payload = build_generation_payload(self.catalog, "model.a", prompt)
        envelope = json.loads(encode_envelope("cuda", "POST", "/generate", payload))
        self.assertEqual(envelope["payload"]["prompt"], prompt)
        self.assertNotIn("touch /tmp/do-not-execute", REMOTE_COMMAND)
        self.assertNotIn(self.fingerprint, REMOTE_COMMAND)
        compile(REMOTE_PROGRAM, "<fixed-remote-helper>", "exec")

    def test_endpoint_and_host_allowlists(self):
        self.assertEqual(HOSTS["gate1"], ("64.247.196.50", 8090))
        self.assertEqual(HOSTS["cuda"], ("64.247.206.118", 8091))
        for args in (("other", "GET", "/models"), ("gate1", "GET", "http://outside/"),
                     ("cuda", "DELETE", "/generate")):
            with self.subTest(args=args), self.assertRaises(ClientError):
                encode_envelope(*args)

    def test_response_identity_is_checked_before_release(self):
        payload = build_generation_payload(self.catalog, "model.a", "hello")
        verify_generation_response(payload, {"model": "model.a", "artifact_fingerprint": self.fingerprint})
        for response in ({"model": "other", "artifact_fingerprint": self.fingerprint},
                         {"model": "model.a", "artifact_fingerprint": "b" * 64},
                         {"model": "model.a", "artifact_fingerprint": "\U0001f30d" * 64},
                         {"model": "model.a"}, None):
            with self.subTest(response=response), self.assertRaises(ClientError):
                verify_generation_response(payload, response)

    def test_prompt_file_size_and_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompt.txt"
            path.write_text("hello\n\U0001f30d", encoding="utf-8")
            self.assertEqual(read_prompt(path), "hello\n\U0001f30d")
            path.write_bytes(b"x" * 65537)
            with self.assertRaisesRegex(ClientError, "prompt_file_too_large"):
                read_prompt(path)
            path.write_bytes(b"\xff")
            with self.assertRaisesRegex(ClientError, "prompt_file_must_be_utf8"):
                read_prompt(path)

    def test_transport_uses_constant_command_and_stdin(self):
        class Channel:
            def shutdown_write(self):
                self.written = True

            def recv_exit_status(self):
                return 0

            def close(self):
                self.closed = True

        class Stream(io.BytesIO):
            pass

        channel = Channel()
        stdin = Stream()
        stdin.channel = channel
        stdout = Stream(b'{"status": 200, "body": {"ok": true}}')
        stdout.channel = channel
        stderr = Stream()

        class FakeClient:
            def exec_command(self, command, timeout):
                self.command = command
                return stdin, stdout, stderr

        session = FleetSession.__new__(FleetSession)
        session.host = "cuda"
        session.client = FakeClient()
        payload = build_generation_payload(self.catalog, "model.a", "$(danger)\n'quoted'")
        response = session.request("POST", "/generate", payload)
        self.assertEqual(response["status"], 200)
        self.assertEqual(session.client.command, REMOTE_COMMAND)
        self.assertEqual(json.loads(stdin.getvalue())["payload"], payload)
        self.assertTrue(channel.closed)


if __name__ == "__main__":
    unittest.main()
