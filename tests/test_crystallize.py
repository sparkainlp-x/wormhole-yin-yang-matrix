"""Tests for Crystallize events in the wormhole. Run from the package root: python3 tests/test_crystallize.py.

Fast by design: the ledger test caps at 5 events (replication
replays stay short). Full bars (4 pairs, 20 events each) are
measured by demo_crystallize.py, not re-run here.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wormhole.crystallize import (FIRST_COMMIT, brier, revise,  # noqa: E402
                                  CrystallizeLedger)
from wormhole.pair import YinYangPair  # noqa: E402


class TestCrystallize(unittest.TestCase):
    def test_brier_and_revise_arithmetic(self):
        self.assertAlmostEqual(brier(0.35, 1), 0.4225)
        self.assertAlmostEqual(brier(1.0, 1), 0.0)
        self.assertAlmostEqual(brier(0.0, 1), 1.0)
        # Agreement: halfway toward the confirmed outcome.
        self.assertAlmostEqual(revise(0.35, 1, 1), 0.675)
        # Disagreement: no revision.
        self.assertAlmostEqual(revise(0.35, 1, 0), 0.35)
        self.assertAlmostEqual(revise(0.35, 0, 1), 0.35)

    def test_adaptive_commit_tracks_history(self):
        pair = YinYangPair(42, 137)
        ledger = CrystallizeLedger(pair)
        self.assertAlmostEqual(ledger._commit("yin->yang")["adaptive"],
                               FIRST_COMMIT)
        self.assertAlmostEqual(ledger._commit("yin->yang")["fixed"],
                               FIRST_COMMIT)
        ledger._history["yin->yang"] = [1, 1, 0]
        self.assertAlmostEqual(ledger._commit("yin->yang")["adaptive"],
                               2.0 / 3.0)
        # Histories are per direction.
        self.assertAlmostEqual(ledger._commit("yang->yin")["adaptive"],
                               FIRST_COMMIT)

    def test_ledger_events_and_non_interference(self):
        pair = YinYangPair(42, 137)
        ledger = CrystallizeLedger(pair, max_events=5)
        summary_with = pair.run(with_wormhole=True, hooks=ledger)
        control = YinYangPair(42, 137)
        summary_without = control.run(with_wormhole=True)
        # The ledger never touches the pair: identical crossings.
        self.assertEqual(summary_with["crossings"], summary_without["crossings"])
        # Events are guard-decided crossings only, capped at 5.
        self.assertEqual(len(ledger.events), 5)
        for event in ledger.events:
            self.assertIsNotNone(event.outcome)
            self.assertIsNotNone(event.replication)
            self.assertEqual(set(event.commits), {"fixed", "probe", "adaptive"})
            self.assertEqual(set(event.revised), {"fixed", "probe", "adaptive"})
        # Every event's outcome matches its crossing record.
        guard = [c for c in summary_with["crossings"]
                 if c["reason"] != "receiver_breaker_open"]
        for event, record in zip(ledger.events, guard):
            self.assertEqual(event.round_no, record["round"])
            self.assertEqual(event.direction, record["direction"])
            self.assertEqual(event.outcome, 1 if record["accepted"] else 0)

    def test_replication_deterministic(self):
        pair = YinYangPair(42, 137)
        ledger = CrystallizeLedger(pair)
        first = ledger._replicate("yin->yang", 3)
        second = ledger._replicate("yin->yang", 3)
        self.assertEqual(first, second)

    def test_ledger_summary_arithmetic(self):
        pair = YinYangPair(42, 137)
        ledger = CrystallizeLedger(pair, max_events=5)
        pair.run(with_wormhole=True, hooks=ledger)
        summary = ledger.summary()
        self.assertEqual(summary["n_events"], 5)
        for strategy in ("fixed", "probe", "adaptive"):
            s = summary[strategy]
            self.assertAlmostEqual(
                s["revision_gain"],
                s["mean_brier_commit"] - s["mean_brier_revised"])
            self.assertAlmostEqual(
                s["score"], (1.0 - s["mean_brier_revised"]) - 0.01)


if __name__ == "__main__":
    unittest.main(verbosity=2)
