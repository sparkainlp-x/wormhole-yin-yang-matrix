"""Tests for black-hole and white-hole cells. Run from the package root: python3 tests/test_holes.py.

The rules are pinned at the mechanism level (masks on the mixture,
frozen guards still deciding, refused crossings committing nothing,
own steps untouched). Fate effects of holes are measured by
demo_holes.py and reported in the README, not re-run here, so the
suite stays fast.
"""

import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wormhole.holes import HoleMap  # noqa: E402
from wormhole.pair import YinYangPair  # noqa: E402


def _state_hash(engine):
    return hashlib.sha256(engine.lattice.state.tobytes()).hexdigest()


def _accepted_transmit(direction, src_holes, dst_holes):
    """First accepted yin->yang transmit over probe pairs 200-229.

    Mirrors the accepted-transmit pattern in tests/tests.py: states
    are re-copied before every attempt, so the expected candidate
    always matches the attempt it is compared against. Returns
    (probe, src_before, dst_before, record) or None.
    """
    for yin_seed in range(200, 230):
        probe = YinYangPair(yin_seed, yin_seed + 1000, coupling=0.1,
                            yin_holes=src_holes, yang_holes=dst_holes)
        src_before = probe.yin.lattice.state.copy()
        dst_before = probe.yang.lattice.state.copy()
        record = probe.wormhole.transmit(
            probe.yin, probe.yang, direction, 1,
            source_holes=probe.yin_holes, dest_holes=probe.yang_holes)
        if record["accepted"]:
            return probe, src_before, dst_before, record
    return None


class TestHoleMap(unittest.TestCase):
    def test_rejects_out_of_grid_cell(self):
        with self.assertRaises(ValueError):
            HoleMap(black=[(3, 0)])
        with self.assertRaises(ValueError):
            HoleMap(white=[(0, -1)])
        with self.assertRaises(ValueError):
            HoleMap(black=[(0, 1, 2)])

    def test_rejects_black_white_clash(self):
        with self.assertRaises(ValueError):
            HoleMap(black=[(1, 1)], white=[(1, 1)])

    def test_masks(self):
        holes = HoleMap(black=[(0, 2)], white=[(2, 0)])
        src = holes.source_mask()
        dst = holes.dest_mask()
        self.assertTrue(src[0, 2])
        self.assertFalse(src[2, 0])
        self.assertTrue(dst[2, 0])
        self.assertFalse(dst[0, 2])
        self.assertEqual(src.sum(), 1)
        self.assertEqual(dst.sum(), 1)

    def test_empty_map_is_falsy(self):
        self.assertFalse(HoleMap())
        self.assertTrue(HoleMap(black=[(1, 1)]))


class TestHoleCrossings(unittest.TestCase):
    def test_mix_black_source_cell_keeps_dest(self):
        pair = YinYangPair(42, 137)
        dest = pair.yang.lattice.state.copy()
        src = pair.yin.lattice.state.copy()
        masked = pair.wormhole.mix(dest, src,
                                   source_black=HoleMap(black=[(1, 1)]).source_mask())
        plain = pair.wormhole.mix(dest, src)
        self.assertTrue(np.array_equal(masked[1, 1], dest[1, 1]))
        self.assertFalse(np.array_equal(masked[1, 1], plain[1, 1]))
        for row in range(3):
            for col in range(3):
                if (row, col) != (1, 1):
                    self.assertTrue(np.array_equal(masked[row, col], plain[row, col]))

    def test_mix_white_dest_cell_keeps_dest(self):
        pair = YinYangPair(42, 137)
        dest = pair.yang.lattice.state.copy()
        src = pair.yin.lattice.state.copy()
        masked = pair.wormhole.mix(dest, src,
                                   dest_white=HoleMap(white=[(0, 0)]).dest_mask())
        plain = pair.wormhole.mix(dest, src)
        self.assertTrue(np.array_equal(masked[0, 0], dest[0, 0]))
        self.assertFalse(np.array_equal(masked[0, 0], plain[0, 0]))

    def test_empty_maps_reproduce_v030(self):
        plain = YinYangPair(42, 137)
        s_plain = plain.run(with_wormhole=True)
        holed = YinYangPair(42, 137, yin_holes=HoleMap(),
                            yang_holes=HoleMap())
        s_holed = holed.run(with_wormhole=True)
        self.assertEqual(s_plain["crossings"], s_holed["crossings"])
        self.assertTrue(np.array_equal(plain.yin.lattice.state,
                                       holed.yin.lattice.state))
        self.assertTrue(np.array_equal(plain.yang.lattice.state,
                                       holed.yang.lattice.state))

    def test_black_source_cell_traps_on_accepted_transmit(self):
        found = _accepted_transmit("yin->yang",
                                   HoleMap(black=[(1, 1)]), HoleMap())
        self.assertIsNotNone(found, "no accepted transmit found in probe pairs 200-229")
        probe, src_before, dst_before, _record = found
        expected = probe.wormhole.mix(
            dst_before, src_before,
            source_black=HoleMap(black=[(1, 1)]).source_mask())
        self.assertTrue(np.array_equal(probe.yang.lattice.state, expected))
        self.assertTrue(np.array_equal(probe.yang.lattice.state[1, 1],
                                       dst_before[1, 1]))

    def test_black_dest_cell_still_receives(self):
        found = _accepted_transmit("yin->yang",
                                   HoleMap(), HoleMap(black=[(2, 2)]))
        self.assertIsNotNone(found, "no accepted transmit found in probe pairs 200-229")
        probe, src_before, dst_before, _record = found
        expected = probe.wormhole.mix(dst_before, src_before)
        self.assertTrue(np.array_equal(probe.yang.lattice.state, expected))
        self.assertFalse(np.array_equal(probe.yang.lattice.state[2, 2],
                                        dst_before[2, 2]))

    def test_white_source_cell_still_emits(self):
        found = _accepted_transmit("yin->yang",
                                   HoleMap(white=[(0, 1)]), HoleMap())
        self.assertIsNotNone(found, "no accepted transmit found in probe pairs 200-229")
        probe, src_before, dst_before, _record = found
        expected = probe.wormhole.mix(dst_before, src_before)
        self.assertTrue(np.array_equal(probe.yang.lattice.state, expected))
        self.assertFalse(np.array_equal(probe.yang.lattice.state[0, 1],
                                        dst_before[0, 1]))

    def test_guard_refusal_with_holes_commits_nothing(self):
        for yin_seed in range(200, 230):
            pair = YinYangPair(yin_seed, yin_seed + 1000,
                               yin_holes=HoleMap(black=[(1, 1)]),
                               yang_holes=HoleMap(white=[(0, 0)]))
            before = _state_hash(pair.yang)
            record = pair.wormhole.transmit(
                pair.yin, pair.yang, "yin->yang", 1,
                source_holes=pair.yin_holes, dest_holes=pair.yang_holes)
            if not record["accepted"] and record["reason"] != "receiver_breaker_open":
                self.assertEqual(_state_hash(pair.yang), before)
                return
        self.fail("no genuine-mix guard refusal found in probe pairs 200-229")

    def test_holes_inert_without_wormhole(self):
        plain = YinYangPair(42, 137)
        s_plain = plain.run(with_wormhole=False)
        holed = YinYangPair(42, 137,
                            yin_holes=HoleMap(black=[(1, 1)]),
                            yang_holes=HoleMap(white=[(1, 1)]))
        s_holed = holed.run(with_wormhole=False)
        self.assertEqual(s_plain["yin_steps"], s_holed["yin_steps"])
        self.assertTrue(np.array_equal(plain.yin.lattice.state,
                                       holed.yin.lattice.state))
        self.assertTrue(np.array_equal(plain.yang.lattice.state,
                                       holed.yang.lattice.state))

    def test_summary_and_frozen_gate_report_holes(self):
        pair = YinYangPair(42, 137,
                           yin_holes=HoleMap(black=[(1, 1)]),
                           yang_holes=HoleMap(white=[(0, 2)]))
        summary = pair.summary()
        self.assertEqual(summary["yin_holes"],
                         {"black": [(1, 1)], "white": []})
        self.assertEqual(summary["yang_holes"],
                         {"black": [], "white": [(0, 2)]})
        gate = pair.frozen_gate()
        self.assertEqual(gate["yin_holes"],
                         {"black": [(1, 1)], "white": []})
        self.assertEqual(gate["yang_holes"],
                         {"black": [], "white": [(0, 2)]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
