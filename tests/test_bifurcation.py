"""Tests for bifurcation symmetry. Run from the package root: python3 tests/test_bifurcation.py.

Fast by design: the sweep smoke test caps at 3 rounds. Full Q1/Q2
numbers are measured by demo_bifurcation.py, not re-run here.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wormhole.bifurcation import (acceptance_asymmetry, classify_fate,  # noqa: E402
                                  state_distance, sweep_pair)
from wormhole.pair import YinYangPair  # noqa: E402


class TestBifurcation(unittest.TestCase):
    def test_state_distance_basics(self):
        a = np.array([[1.0 + 0j, 0.0], [0.0, 1.0]])
        self.assertAlmostEqual(state_distance(a, a), 0.0)
        b = np.zeros((2, 2), dtype=complex)
        self.assertAlmostEqual(state_distance(a, b), 1.0)
        self.assertAlmostEqual(state_distance(a, b), state_distance(b, a))
        c = 2.0 * a
        self.assertAlmostEqual(state_distance(a, c), 1.0 / 3.0)

    def test_classify_fate_all_four(self):
        self.assertEqual(classify_fate(10, 10, 200), "control-like")
        self.assertEqual(classify_fate(200, 10, 200), "yin-runaway")
        self.assertEqual(classify_fate(10, 200, 200), "yang-runaway")
        self.assertEqual(classify_fate(200, 200, 200), "both-runaway")
        self.assertEqual(classify_fate(50, 10, 50), "yin-runaway")

    def test_acceptance_asymmetry_ignores_breaker_closed(self):
        crossings = [
            {"direction": "yin->yang", "accepted": True, "reason": "ok"},
            {"direction": "yin->yang", "accepted": False, "reason": "ok"},
            {"direction": "yin->yang", "accepted": False,
             "reason": "receiver_breaker_open"},
            {"direction": "yang->yin", "accepted": True, "reason": "ok"},
        ]
        # Guard-decided: yin->yang 1/2 = 0.5, yang->yin 1/1 = 1.0.
        self.assertAlmostEqual(acceptance_asymmetry(crossings), -0.5)

    def test_crossing_order_flag(self):
        first = YinYangPair(42, 137, crossing_order="yin-first")
        second = YinYangPair(42, 137, crossing_order="yang-first")
        for _ in range(3):
            first.run_round(with_wormhole=True)
            second.run_round(with_wormhole=True)
        self.assertEqual(first.crossings[0]["direction"], "yin->yang")
        self.assertEqual(second.crossings[0]["direction"], "yang->yin")
        with self.assertRaises(ValueError):
            YinYangPair(42, 137, crossing_order="sideways")

    def test_default_order_unchanged(self):
        # Default pair must behave exactly like v0.2.0: yin-first.
        pair = YinYangPair(42, 137)
        self.assertEqual(pair.crossing_order, "yin-first")
        pair.run(with_wormhole=True)
        self.assertEqual(pair.crossings[0]["direction"], "yin->yang")

    def test_sweep_pair_smoke(self):
        row = sweep_pair(42, 137, 0.5, max_rounds=3)
        self.assertEqual(row["n_rounds"], 3)
        # Fate at a 3-round cap is "both-runaway" by definition (both
        # reached the cap); fate logic itself is pinned above.
        self.assertEqual(row["fate"], "both-runaway")
        self.assertGreaterEqual(row["distance_initial"], 0.0)
        self.assertLessEqual(row["distance_final"], 1.0)
        self.assertEqual(row["asymmetry"], row["asymmetry"])  # not NaN


if __name__ == "__main__":
    unittest.main(verbosity=2)
