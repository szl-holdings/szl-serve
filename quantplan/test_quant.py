import unittest

from quantplan.quant import (KNOWN_QUANTS, QuantError, plan, validated_quant)


class TableTests(unittest.TestCase):
    def test_table_completeness_every_quant_has_bpw(self):
        for q, bpw in KNOWN_QUANTS.items():
            self.assertIsInstance(bpw, float)
            self.assertGreater(bpw, 0)
            self.assertEqual(validated_quant(q), bpw)

    def test_size_monotonic_in_bpw_for_fixed_params(self):
        # Estimated bytes are monotone in the DECLARED bpw constants for a
        # fixed n_params (Kimi W32 amend 2): iterated in ascending-bpw order
        # the estimates are nondecreasing, equivalently non-increasing when
        # iterated in descending-bpw order. Entries are compared only as
        # declared constants; no global quality ranking of the table is
        # asserted (Q5_K_S 5.5 < Q5_K_M 5.69 and Q4_K_S 4.5 < Q4_K_M 4.85
        # are declared as-is).
        n = 1_000_000
        prev = None
        for q, bpw in sorted(KNOWN_QUANTS.items(), key=lambda kv: kv[1]):
            est = plan(n, q)["estimated_bytes"]
            if prev is not None:
                self.assertLessEqual(prev, est)
            prev = est

    def test_exact_math_q8_0(self):
        # ceil(1_000_000 * 8.5 / 8) == ceil(1_062_500) == 1_062_500
        self.assertEqual(plan(1_000_000, "Q8_0")["estimated_bytes"], 1_062_500)


class PlanTests(unittest.TestCase):
    def test_unknown_quant_rejected(self):
        with self.assertRaises(QuantError):
            plan(1_000, "Q4_TOTALLY_MADE_UP")
        with self.assertRaises(QuantError):
            validated_quant("q4_k_m")  # case-sensitive, unknown

    def test_unknown_source_quant_rejected(self):
        # Kimi W32 amend 1: unknown sources raise, never silently unquantized.
        with self.assertRaises(QuantError):
            plan(1_000, "Q4_K_M", source="TOTALLY_UNKNOWN_FORMAT")
        with self.assertRaises(QuantError):
            plan(1_000, "Q4_K_M", source="")
        with self.assertRaises(QuantError):
            plan(1_000, "Q4_K_M", source="fp16")

    def test_quantized_source_rejected(self):
        with self.assertRaises(QuantError):
            plan(1_000, "Q4_K_M", source="Q8_0")  # quantizing-from-quantized
        with self.assertRaises(QuantError):
            plan(1_000, "Q4_K_M", source="q4_k_m")

    def test_non_positive_params_rejected(self):
        for bad in (0, -1, True):  # zero, negative, and bool all rejected
            with self.assertRaises(QuantError):
                plan(bad, "Q4_K_M")
        with self.assertRaises(QuantError):
            plan(1.5, "Q4_K_M")  # not an int

    def test_valid_plan_shape(self):
        p = plan(7_000_000_000, "Q4_K_M", source="F16")
        self.assertEqual(p["schema_version"], "szl.quantplan/v1")
        self.assertEqual(p["banner"], "PROPOSAL_ONLY_UNSIGNED")
        self.assertIn("no conversion executed", p["estimate_disclosure"])


if __name__ == "__main__":
    unittest.main()
