"""Tests for wormhole-yin-yang-matrix. Run from the package root: python3 tests/tests.py.

Tests pin the MECHANISM (refused crossings commit nothing, accepted
crossings commit validated mixtures, observer non-mutation,
determinism, frozen gate, calibrator gate logic, vendored bytes,
NumPy declaration). Full bar 1 (21 pairs) and bar 2 (100 probe pairs)
numbers are measured by demo.py and reported in the README, not re-run
here, so the suite stays fast.
"""

import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wormhole.bars import BAR2_YIN_SEEDS  # noqa: E402
from wormhole.calibrator import WormholeCalibrator  # noqa: E402
from wormhole.observer import JUNK_SALT, WormholeObserver  # noqa: E402
from wormhole.pair import YinYangPair  # noqa: E402


def _state_hash(engine):
    return hashlib.sha256(engine.lattice.state.tobytes()).hexdigest()


class TestWormhole(unittest.TestCase):
    def test_probe_junk_refused_and_state_unchanged(self):
        pair = YinYangPair(42, 137)
        before = _state_hash(pair.yang)
        rng = np.random.default_rng([42, JUNK_SALT])
        shape = pair.yang.lattice.state.shape
        junk = rng.uniform(size=shape) + 1j * rng.uniform(size=shape)
        mixed_junk = pair.wormhole.mix(pair.yang.lattice.state, junk)
        ok, reason = pair.yang._validate(mixed_junk)
        self.assertFalse(ok)
        self.assertEqual(_state_hash(pair.yang), before)

    def test_observer_snapshot_does_not_mutate(self):
        pair = YinYangPair(42, 137)
        observer = WormholeObserver(pair)
        before = observer.snapshot(pair.yin)
        for _ in range(3):
            observer.snapshot(pair.yin)
            observer.snapshot(pair.yang)
        after = observer.snapshot(pair.yin)
        self.assertEqual(before, after)
        self.assertEqual(len(pair.yin.calibrations), 0)
        self.assertEqual(len(pair.yin.observations), 0)

    def test_transmit_guard_refusal_commits_nothing(self):
        # Search fixed probe pairs for a genuine-mix guard refusal
        # (deterministic: same seeds give the same outcome every run).
        for yin_seed in range(200, 230):
            pair = YinYangPair(yin_seed, yin_seed + 1000)
            before = _state_hash(pair.yang)
            record = pair.wormhole.transmit(pair.yin, pair.yang,
                                            "yin->yang", 1)
            if not record["accepted"] and record["reason"] != "receiver_breaker_open":
                self.assertEqual(_state_hash(pair.yang), before)
                return
        self.fail("no genuine-mix guard refusal found in probe pairs 200-229")

    def test_transmit_accepted_commits_mixed_candidate(self):
        # At the default coupling 0.5, initial-state mixes are refused
        # (purity_too_low — the measured probe result, pinned by the
        # refusal test and demo bar 2). The accepted path is exercised
        # at coupling 0.1, where probe pairs pass 30/30, and in pair
        # runs at 0.5, where post-step crossings pass and the pair
        # converges (pinned by test_pair_run_records_consistent).
        for yin_seed in range(200, 230):
            pair = YinYangPair(yin_seed, yin_seed + 1000, coupling=0.1)
            yin_before = pair.yin.lattice.state.copy()
            yang_before = pair.yang.lattice.state.copy()
            record = pair.wormhole.transmit(pair.yin, pair.yang,
                                            "yin->yang", 1)
            if record["accepted"]:
                self.assertEqual(record["reason"], "ok")
                expected = pair.wormhole.mix(yang_before, yin_before)
                self.assertTrue(np.array_equal(pair.yang.lattice.state, expected))
                return
        self.fail("no accepted transmit found in probe pairs 200-229")

    def test_pair_run_records_consistent(self):
        pair = YinYangPair(42, 137)
        summary = pair.run(with_wormhole=True)
        self.assertEqual(summary["crossings_attempted"], 2 * summary["rounds"])
        self.assertEqual(summary["crossings_guard_decided"]
                         + summary["crossings_breaker_closed"],
                         summary["crossings_attempted"])
        for record in summary["crossings"]:
            if record["accepted"]:
                self.assertEqual(record["reason"], "ok")

    def test_determinism(self):
        first = YinYangPair(42, 137)
        s1 = first.run(with_wormhole=True)
        second = YinYangPair(42, 137)
        s2 = second.run(with_wormhole=True)
        for key in ("yin_steps", "yin_accepted", "yang_steps", "yang_accepted",
                    "crossings_attempted", "crossings_accepted"):
            self.assertEqual(s1[key], s2[key], key)
        self.assertEqual(s1["crossings"], s2["crossings"])

    def test_frozen_gate_unchanged(self):
        pair = YinYangPair(42, 137)
        before = pair.frozen_gate()
        pair.run(with_wormhole=True)
        observer = WormholeObserver(pair)
        for seed in (200, 201, 202):
            observer.probe_gate(seed, seed + 1000)
        self.assertEqual(pair.frozen_gate(), before)

    def test_gate_paths_agree_subset(self):
        pair = YinYangPair(42, 137)
        observer = WormholeObserver(pair)
        for yin_seed in (200, 201, 202, 203, 204):
            clean_ref, junk_ref, _cr, _jr = observer.probe_gate(
                yin_seed, yin_seed + 1000)
            direct = YinYangPair(yin_seed, yin_seed + 1000)
            clean_ok, _r = direct.wormhole.probe(direct.yin, direct.yang)
            rng = np.random.default_rng([int(yin_seed), JUNK_SALT])
            shape = direct.yang.lattice.state.shape
            junk = rng.uniform(size=shape) + 1j * rng.uniform(size=shape)
            mixed_junk = direct.wormhole.mix(direct.yang.lattice.state, junk)
            junk_ok, _r2 = direct.yang._validate(mixed_junk)
            self.assertEqual(clean_ref, not clean_ok, yin_seed)
            self.assertEqual(junk_ref, not junk_ok, yin_seed)

    def test_calibrator_gate_logic(self):
        # Gate-logic checks with hand-built reports (the measured
        # scenarios run in demo.py). Nothing here measures the arena.
        from wormhole.observer import Report
        pair = YinYangPair(42, 137)
        cal = WormholeCalibrator(pair)
        good = [Report("gate-aggregate",
                       {"clean_refusal_rate": 0.1, "junk_refusal_rate": 0.9},
                       half_width=0.05, n=100)
                for _ in range(3)]
        saved = dict(pair.gates)
        pair.gates["gate_calibrated"] = False
        _v, cap = cal.calibrate(good)
        self.assertEqual(cap.reason, "gate_not_calibrated")
        pair.gates.update(saved)
        _v, cap = cal.calibrate(good)
        self.assertEqual(cap.reason, "review_signoff_missing")
        pair.set_review_signoff(True)
        pair.gates["money_gates_pass"] = False
        _v, cap = cal.calibrate(good)
        self.assertEqual(cap.reason, "money_gates_failed")
        pair.gates.update(saved)
        pair.set_review_signoff(True)
        _v, cap = cal.calibrate(good[:2])
        self.assertEqual(cap.reason, "too_few_reports")
        bad = list(good)
        bad[0] = Report("gate-aggregate",
                        {"clean_refusal_rate": 0.1, "junk_refusal_rate": 0.9},
                        half_width=0.25, n=100)
        _v, cap = cal.calibrate(bad)
        self.assertEqual(cap.reason, "half_width_too_wide")
        before = pair.frozen_gate()
        applied, cap = cal.calibrate(good)
        self.assertIsNone(cap)
        self.assertTrue(cal.apply(applied))
        self.assertEqual(pair.frozen_gate(), before)
        pair.gates.update(saved)
        pair.set_review_signoff(False)

    def test_vendored_bytes_match_provenance(self):
        recorded = {}
        for line in (ROOT / "VENDORED_SHA256.txt").read_text().splitlines():
            digest, path = line.split(None, 1)
            recorded[path.strip()] = digest
        vendored = ROOT / "membrane_arena_3x3"
        for path, digest in recorded.items():
            actual = hashlib.sha256((vendored / path).read_bytes()).hexdigest()
            self.assertEqual(actual, digest, path)

    def test_numpy_declared(self):
        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn("numpy", pyproject)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("NumPy", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
