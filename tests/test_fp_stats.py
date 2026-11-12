"""Unit tests for false-positive statistical estimators (Garwood Poisson, Wilson, Rule of Three)."""

import math
import unittest
from tests.fp.tools.stats import poisson_ci, rule_of_three, wilson


class TestFpStats(unittest.TestCase):
    def test_zero_event_poisson_and_rule_of_three(self):
        lo, hi = poisson_ci(0, 1.0)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 3.688879, places=4)

        r3 = rule_of_three(10.0)
        self.assertAlmostEqual(r3, 0.3, places=6)

    def test_known_answer_garwood_poisson(self):
        # For k=5, exposure=10.0: chi2(10, 0.025)/20 ~ 0.16235, chi2(12, 0.975)/20 ~ 1.16683
        lo, hi = poisson_ci(5, 10.0)
        self.assertAlmostEqual(lo, 0.16235, places=4)
        self.assertAlmostEqual(hi, 1.16683, places=4)

        # Interval widens inversely with exposure
        lo_small, hi_small = poisson_ci(5, 1.0)
        self.assertAlmostEqual(lo_small, lo * 10.0, places=3)
        self.assertAlmostEqual(hi_small, hi * 10.0, places=3)

    def test_wilson_score_intervals(self):
        # 0 successes out of 20
        lo_0, hi_0 = wilson(0, 20)
        self.assertEqual(lo_0, 0.0)
        self.assertAlmostEqual(hi_0, 0.1611, places=3)

        # 20 successes out of 20
        lo_full, hi_full = wilson(20, 20)
        self.assertEqual(hi_full, 1.0)
        self.assertAlmostEqual(lo_full, 0.8389, places=3)

        # n = 0 edge case returns (nan, nan)
        nan_lo, nan_hi = wilson(0, 0)
        self.assertTrue(math.isnan(nan_lo))
        self.assertTrue(math.isnan(nan_hi))

    def test_invalid_parameters_raise(self):
        with self.assertRaises(ValueError):
            poisson_ci(-1, 10.0)
        with self.assertRaises(ValueError):
            poisson_ci(5, 0.0)
        with self.assertRaises(ValueError):
            rule_of_three(-5.0)
        with self.assertRaises(ValueError):
            wilson(5, 4)


if __name__ == "__main__":
    unittest.main()
