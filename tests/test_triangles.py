"""Tests for triangle hole patterns. Run from the package root: python3 tests/test_triangles.py.

Pinned at the mechanism level (triangle geometry, masks on the
mixture, the structural black-on-yin == white-on-yang identity,
guards still deciding). Fate effects are measured by
demo_triangles.py and reported in the README, not re-run here,
except the identity check, which is exact and cheap.
"""

import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wormhole.holes import HoleMap  # noqa: E402
from wormhole.pair import YinYangPair  # noqa: E402
from wormhole.triangles import (  # noqa: E402
    TRIANGLE_CELLS, is_triangle, triangle_area2, triangle_black,
    triangle_white)


class TestTriangleGeometry(unittest.TestCase):
    def test_three_distinct_in_grid_cells(self):
        self.assertEqual(len(TRIANGLE_CELLS), 3)
        self.assertEqual(len(set(TRIANGLE_CELLS)), 3)
        for row, col in TRIANGLE_CELLS:
            self.assertTrue(0 <= row < 3 and 0 <= col < 3)

    def test_is_triangle(self):
        self.assertTrue(is_triangle(TRIANGLE_CELLS))
        self.assertFalse(is_triangle([(0, 0), (1, 1), (2, 2)]))
        self.assertFalse(is_triangle([(0, 0), (0, 0), (2, 0)]))
        self.assertFalse(is_triangle([(0, 0), (3, 0), (2, 0)]))
        self.assertFalse(is_triangle([(0, 0), (0, 2)]))

    def test_right_isosceles_not_equilateral(self):
        (x1, y1), (x2, y2), (x3, y3) = TRIANGLE_CELLS
        sides = sorted([
            math.dist((x1, y1), (x2, y2)),
            math.dist((x2, y2), (x3, y3)),
            math.dist((x3, y3), (x1, y1))])
        self.assertEqual(triangle_area2(), 4)
        self.assertAlmostEqual(sides[0], 2.0)
        self.assertAlmostEqual(sides[1], 2.0)
        self.assertAlmostEqual(sides[2], 2.0 * math.sqrt(2.0))
        self.assertAlmostEqual(sides[0] ** 2 + sides[1] ** 2,
                               sides[2] ** 2)
        self.assertNotAlmostEqual(sides[0], sides[2])

    def test_constructors(self):
        black = triangle_black()
        white = triangle_white()
        self.assertEqual(black.cells(),
                         {"black": sorted(TRIANGLE_CELLS), "white": []})
        self.assertEqual(white.cells(),
                         {"black": [], "white": sorted(TRIANGLE_CELLS)})
        with self.assertRaises(ValueError):
            triangle_black([(0, 0), (1, 1), (2, 2)])


class TestTriangleCrossings(unittest.TestCase):
    def test_mix_black_triangle_keeps_dest_cells(self):
        pair = YinYangPair(42, 137)
        dest = pair.yang.lattice.state.copy()
        src = pair.yin.lattice.state.copy()
        masked = pair.wormhole.mix(
            dest, src, source_black=triangle_black().source_mask())
        plain = pair.wormhole.mix(dest, src)
        for row in range(3):
            for col in range(3):
                if (row, col) in TRIANGLE_CELLS:
                    self.assertTrue(np.array_equal(masked[row, col],
                                                   dest[row, col]))
                    self.assertFalse(np.array_equal(masked[row, col],
                                                    plain[row, col]))
                else:
                    self.assertTrue(np.array_equal(masked[row, col],
                                                   plain[row, col]))

    def test_mix_white_triangle_keeps_dest_cells(self):
        pair = YinYangPair(42, 137)
        dest = pair.yang.lattice.state.copy()
        src = pair.yin.lattice.state.copy()
        masked = pair.wormhole.mix(
            dest, src, dest_white=triangle_white().dest_mask())
        plain = pair.wormhole.mix(dest, src)
        for row in range(3):
            for col in range(3):
                if (row, col) in TRIANGLE_CELLS:
                    self.assertTrue(np.array_equal(masked[row, col],
                                                   dest[row, col]))
                else:
                    self.assertTrue(np.array_equal(masked[row, col],
                                                   plain[row, col]))

    def test_black_on_yin_equals_white_on_yang_exactly(self):
        for yin_seed, yang_seed in ((0, 1000), (1, 1001)):
            black_pair = YinYangPair(yin_seed, yang_seed, coupling=0.5,
                                     yin_holes=triangle_black(),
                                     yang_holes=None)
            white_pair = YinYangPair(yin_seed, yang_seed, coupling=0.5,
                                     yin_holes=None,
                                     yang_holes=triangle_white())
            black_pair.run(max_rounds=50)
            white_pair.run(max_rounds=50)
            self.assertEqual(black_pair.summary()["crossings"],
                             white_pair.summary()["crossings"])
            self.assertTrue(np.array_equal(black_pair.yin.lattice.state,
                                           white_pair.yin.lattice.state))
            self.assertTrue(np.array_equal(black_pair.yang.lattice.state,
                                           white_pair.yang.lattice.state))

    def test_black_on_both_masks_both_directions(self):
        for yin_seed in range(200, 230):
            pair = YinYangPair(yin_seed, yin_seed + 1000, coupling=0.1,
                               yin_holes=triangle_black(),
                               yang_holes=triangle_black())
            src_before = pair.yang.lattice.state.copy()
            dst_before = pair.yin.lattice.state.copy()
            record = pair.wormhole.transmit(
                pair.yang, pair.yin, "yang->yin", 1,
                source_holes=pair.yang_holes, dest_holes=pair.yin_holes)
            if record["accepted"]:
                for cell in TRIANGLE_CELLS:
                    self.assertTrue(np.array_equal(
                        pair.yin.lattice.state[cell], dst_before[cell]))
                expected = pair.wormhole.mix(
                    dst_before, src_before,
                    source_black=triangle_black().source_mask())
                self.assertTrue(np.array_equal(pair.yin.lattice.state,
                                               expected))
                return
        self.fail("no accepted yang->yin transmit found in probe pairs 200-229")

    def test_summary_reports_triangle(self):
        pair = YinYangPair(42, 137, yin_holes=triangle_black(),
                           yang_holes=triangle_white())
        summary = pair.summary()
        self.assertEqual(summary["yin_holes"],
                         {"black": sorted(TRIANGLE_CELLS), "white": []})
        self.assertEqual(summary["yang_holes"],
                         {"black": [], "white": sorted(TRIANGLE_CELLS)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
