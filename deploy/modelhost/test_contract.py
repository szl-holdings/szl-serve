"""Regression checks for artifact identity, fail-closed readiness and admission."""

import itertools
import json
import threading
import time
import unittest

from contract import (AdmissionRejected, BoundedAdmission, ContractError,
                      choose_adapter_config, readiness_summary,
                      validate_generation_request)


class AdapterSelectionTests(unittest.TestCase):
    def test_release_wins_over_newer_checkpoints_in_every_order(self):
        files = ["final/adapter_config.json", "checkpoint-9999/adapter_config.json",
                 "checkpoint-2/adapter_config.json", "README.md"]
        for permutation in itertools.permutations(files):
            self.assertEqual(choose_adapter_config(permutation), "final/adapter_config.json")

    def test_existing_shallow_release_precedence(self):
        self.assertEqual(choose_adapter_config(["z/final/adapter_config.json",
                                               "final/adapter_config.json", "adapter_config.json"]),
                         "adapter_config.json")

    def test_checkpoint_steps_are_numeric_and_ties_deterministic(self):
        files = ["z/checkpoint-10/adapter_config.json", "checkpoint-9/adapter_config.json",
                 "a/checkpoint-10/adapter_config.json"]
        for permutation in itertools.permutations(files):
            self.assertEqual(choose_adapter_config(permutation), "a/checkpoint-10/adapter_config.json")

    def test_non_artifact_and_empty_lists_do_not_choose_another_file(self):
        for files in ([], ["adapter_config.json.bak"], ["README.md"]):
            with self.assertRaises(ContractError) as ctx:
                choose_adapter_config(files)
            self.assertEqual(ctx.exception.code, "adapter_config_missing")

    def test_unsafe_paths_rejected_even_with_valid_release(self):
        for path in ("../adapter_config.json", "/adapter_config.json", "C:/adapter_config.json",
                     "x\\adapter_config.json", "./adapter_config.json", "x//adapter_config.json",
                     "x/../adapter_config.json", "x/\x00bad", "x/\nBAD"):
            with self.subTest(path=path), self.assertRaises(ContractError):
                choose_adapter_config(["final/adapter_config.json", path])

    def test_malformed_checkpoint_is_not_a_release(self):
        with self.assertRaises(ContractError) as ctx:
            choose_adapter_config(["checkpoint-latest/adapter_config.json"])
        self.assertEqual(ctx.exception.code, "invalid_checkpoint_path")

    def test_iterable_type_errors_are_explicit(self):
        for value in (None, "adapter_config.json", [None]):
            with self.subTest(value=value), self.assertRaises(ContractError):
                choose_adapter_config(value)


class GenerationValidationTests(unittest.TestCase):
    def test_valid_boundaries_and_default(self):
        self.assertEqual(validate_generation_request({"model": "a.1", "prompt": ""}), ("a.1", "", 256))
        self.assertEqual(validate_generation_request({"model": "a", "prompt": "x" * 4,
                                                     "max_new_tokens": 7}, 4, 7), ("a", "xxxx", 7))
        self.assertEqual(validate_generation_request({"model": "a", "prompt": "p"}, 4, 7)[2], 7)

    def test_no_integer_coercion(self):
        for count in (True, False, 1.0, 2.5, "4", None, 0, -1, 513):
            with self.subTest(count=count), self.assertRaises(ContractError) as ctx:
                validate_generation_request({"model": "m", "prompt": "x", "max_new_tokens": count})
            self.assertEqual(ctx.exception.code, "invalid_max_new_tokens")

    def test_wrong_request_and_field_types(self):
        for request in (None, [], "x", 1, {"model": "m"}, {"model": "m", "prompt": ["x"]},
                        {"model": "", "prompt": "x"}, {"model": " m", "prompt": "x"},
                        {"model": "m\n", "prompt": "x"}, {"model": "x" * 257, "prompt": "x"}):
            with self.subTest(request=request), self.assertRaises(ContractError):
                validate_generation_request(request)

    def test_prompt_is_rejected_without_silent_truncation(self):
        with self.assertRaises(ContractError) as ctx:
            validate_generation_request({"model": "m", "prompt": "abcde"}, max_prompt_chars=4)
        self.assertEqual(ctx.exception.code, "prompt_too_large")

    def test_untrusted_generation_options_are_not_returned(self):
        self.assertEqual(validate_generation_request({"model": "m", "prompt": "x", "do_sample": True,
                                                     "num_beams": 1000}), ("m", "x", 256))


class ReadinessTests(unittest.TestCase):
    def good_state(self):
        return {"status": "loaded", "identity_verified": True, "canary_ok": True}

    def summary(self, manifest, states, **kwargs):
        args = {"free_disk_bytes": 60 * 1024**3, "free_vram_mb": 6000}
        args.update(kwargs)
        return readiness_summary(manifest, states, **args)

    def test_loaded_is_not_evidence_verified(self):
        result = self.summary(["SZLHOLDINGS/a"], {"a": {"status": "loaded"}})
        self.assertFalse(result["ready"])
        self.assertEqual(result["http_status"], 503)
        self.assertEqual(result["loaded_count"], 1)
        self.assertEqual(result["unverified"], ["a"])

    def test_failed_list_entry_cannot_disappear_from_denominator(self):
        result = self.summary(["a", "b", "c"], {"a": self.good_state(),
                                                 "b": {"status": "error:credential=do-not-expose"}})
        self.assertEqual(result["configured_count"], 3)
        self.assertEqual(result["required_count"], 3)
        self.assertEqual(result["missing"], ["c"])
        self.assertEqual(result["unavailable"], {"b": "error"})
        self.assertNotIn("do-not-expose", json.dumps(result))
        self.assertFalse(result["ready"])

    def test_explicit_capacity_exclusions_preserve_total(self):
        result = self.summary(["a", "b"], {"a": self.good_state(), "b": "no-vram-base"},
                              intentional_exclusions=["b"])
        self.assertTrue(result["ready"])
        self.assertEqual((result["configured_count"], result["required_count"], result["excluded_count"]),
                         (2, 1, 1))
        self.assertEqual(result["intentional_exclusions"], ["b"])

    def test_missing_or_invalid_pressure_never_promotes_readiness(self):
        for field in ("free_disk_bytes", "free_vram_mb"):
            for invalid in (None, True, False, -1, float("nan"), float("inf"), "6000"):
                with self.subTest(field=field, invalid=invalid):
                    result = self.summary(["a"], {"a": self.good_state()}, **{field: invalid})
                    self.assertFalse(result["ready"])
                    json.dumps(result, allow_nan=False)

    def test_low_disk_blocks_admission_without_mutating_model(self):
        states = {"a": self.good_state()}
        result = self.summary(["a"], states, free_disk_bytes=17 * 1024**3)
        self.assertIn("disk_below_reserve", result["reasons"])
        self.assertEqual(states, {"a": self.good_state()})

    def test_empty_manifest_all_excluded_and_starting_are_not_ready(self):
        self.assertFalse(self.summary([], {})["ready"])
        self.assertFalse(self.summary(["a"], {}, intentional_exclusions=["a"])["ready"])
        self.assertFalse(self.summary(["a"], {"a": self.good_state()}, initialization_complete=False)["ready"])

    def test_exact_booleans_required_for_verification(self):
        for field in ("identity_verified", "canary_ok"):
            state = self.good_state()
            state[field] = 1
            self.assertFalse(self.summary(["a"], {"a": state})["ready"])

    def test_duplicate_names_and_unknown_exclusions_are_errors(self):
        for manifest, states, exclusions in ((["org/a", "other/a"], {}, []),
                                            (["a"], {}, ["unknown"]),
                                            (["a"], {"org/a": "loaded", "other/a": "loaded"}, [])):
            with self.assertRaises(ContractError):
                self.summary(manifest, states, intentional_exclusions=exclusions)

    def test_manifest_mapping_and_unexpected_observation(self):
        result = self.summary([{"repo_id": "SZLHOLDINGS/a"}],
                              {"a": self.good_state(), "unexpected": self.good_state()})
        self.assertFalse(result["ready"])
        self.assertEqual(result["loaded_count"], 1)
        self.assertEqual(result["unexpected"], ["unexpected"])
        self.assertIn("unexpected_models_observed", result["reasons"])


class BoundedAdmissionTests(unittest.TestCase):
    def wait_until_queued(self, gate, count=1):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if gate.snapshot()["queued"] == count:
                return
            threading.Event().wait(0.002)
        self.fail("worker did not enter admission queue")

    def test_capacity_queue_bound_and_release_wakes_waiter(self):
        gate = BoundedAdmission(max_inflight=1, max_queue=1)
        gate.acquire()
        entered = threading.Event()
        errors = []
        def worker():
            try:
                with gate.slot(timeout=2):
                    entered.set()
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=worker)
        thread.start()
        self.wait_until_queued(gate)
        with self.assertRaises(AdmissionRejected) as ctx:
            gate.acquire(timeout=1)
        self.assertEqual(ctx.exception.code, "busy")
        self.assertFalse(entered.is_set())
        gate.release()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(entered.is_set())
        self.assertEqual((gate.snapshot()["active"], gate.snapshot()["queued"]), (0, 0))

    def test_timeout_does_not_leak_waiter_or_active_slot(self):
        gate = BoundedAdmission()
        with gate.slot():
            with self.assertRaises(AdmissionRejected) as ctx:
                gate.acquire(timeout=0.02)
            self.assertEqual(ctx.exception.code, "queue_timeout")
            self.assertEqual((gate.snapshot()["active"], gate.snapshot()["queued"]), (1, 0))
        with gate.slot():
            self.assertEqual(gate.snapshot()["active"], 1)

    def test_waiters_are_admitted_in_fifo_order(self):
        gate = BoundedAdmission(max_inflight=1, max_queue=2)
        gate.acquire()
        order, errors = [], []
        def worker(name):
            try:
                with gate.slot(timeout=2):
                    order.append(name)
            except BaseException as exc:
                errors.append(exc)
        first = threading.Thread(target=worker, args=("first",))
        second = threading.Thread(target=worker, args=("second",))
        first.start()
        self.wait_until_queued(gate, 1)
        second.start()
        self.wait_until_queued(gate, 2)
        gate.release()
        first.join(timeout=2)
        second.join(timeout=2)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(order, ["first", "second"])

    def test_exception_in_generation_releases_slot(self):
        gate = BoundedAdmission(max_queue=0)
        with self.assertRaisesRegex(RuntimeError, "generation failed"):
            with gate.slot():
                raise RuntimeError("generation failed")
        with gate.slot():
            self.assertEqual(gate.snapshot()["active"], 1)

    def test_invalid_configuration_and_unmatched_release(self):
        for config in ({"max_inflight": True}, {"max_inflight": 0}, {"max_queue": -1}):
            with self.assertRaises(ContractError):
                BoundedAdmission(**config)
        gate = BoundedAdmission()
        for timeout in (True, -1, float("inf"), float("nan")):
            with self.assertRaises(ContractError):
                gate.acquire(timeout)
        with self.assertRaises(RuntimeError):
            gate.release()


if __name__ == "__main__":
    unittest.main(verbosity=2)
