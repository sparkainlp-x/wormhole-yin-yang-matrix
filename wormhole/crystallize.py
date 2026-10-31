"""Crystallize events in the wormhole: commit, replicate, revise.

The Crystallize game, applied to wormhole crossings: before a
crossing, commit a probability that the guard will accept it; the
crossing resolves the outcome; a simulated Reviewer 2 replicates the
same crossing protocol on fresh membranes; then revise. Scored on
calibration minus sampling cost.

Preregistered bars (measure all, tune none):
- C1 calibration: mean Brier score of commits vs outcomes, per
  commit strategy (fixed, probe, adaptive) — pooled over events.
- C2 replication agreement: fraction of events where the Reviewer-2
  outcome equals the original outcome.
- C3 revision value: mean Brier(commit) - mean Brier(revised), per
  strategy, under the stated revision rule (see ``revise``). The rule
  is arithmetic, not a discovery: on agreement it quarters the
  Brier score; on disagreement it changes nothing. The empirical
  content is C1 and C2; C3 is their consequence, reported as such.
- Score: (1 - mean Brier revised) - COST_PER_REPLICATION, one
  replication per event. All components are reported separately so
  the combined score is auditable.

Definitions, stated exactly:
- An EVENT is one guard-decided crossing (reason !=
  ``receiver_breaker_open``). Breaker-closed crossings are not
  events: the wormhole was closed, no guard decision exists.
- Commit strategies (per direction, history is that direction's
  past outcomes in this run):
  - ``fixed``: FIRST_COMMIT (0.35, the arena injection's
    first_commit) for every event.
  - ``probe``: 1.0 if the pair's initial probe in that direction
    was accepted, else 0.0. Measured once per pair, before the run.
  - ``adaptive``: the running mean of past outcomes in that
    direction, starting at FIRST_COMMIT for the first event. This
    is the membrane lesson (a fixed commit is wrong on an evolved
    system; tracking the empirical rate is the honest mechanism).
- Reviewer 2 (replication): a fresh pair (seeds + 5000) runs the
  SAME protocol with the wormhole to round_no - 1, then PROBES
  (validate-only, never commits) the round_no crossing in the same
  direction. Fresh membranes, same stage, same coupling. Outcome 1
  if the probe passes, else 0 (including breaker-closed replications,
  whose reason is recorded).
- Revision rule: if replication agrees with the outcome,
  revised = (committed + outcome) / 2; else revised = committed.
  Agreement gates revision: conflicting evidence changes nothing.
- Scope limit, stated openly: a ledger records at most MAX_EVENTS
  (default 20) events per pair, the FIRST 20 in order — no selection
  on outcome. This bounds replication cost (each replay runs up to
  round_no rounds). Runaway pairs are excluded from the crystallize
  demo for the same reason (a 200-round replay per event); that is a
  cost bound, not a result claim.
- The ledger never touches its pair: hooks observe records only,
  and every replication runs on separate fresh pairs. A pair run
  with a ledger produces byte-identical crossings to the same run
  without one (pinned by test).
"""

from __future__ import annotations

FIRST_COMMIT = 0.35
REPLICATION_SEED_OFFSET = 5000
COST_PER_REPLICATION = 0.01
MAX_EVENTS = 20
STRATEGIES = ("fixed", "probe", "adaptive")


def brier(probability, outcome):
    """Brier score: (p - o)^2. Lower is better calibrated."""
    return (probability - outcome) ** 2


def revise(committed, outcome, replication):
    """Agreement-gated revision: halfway toward a confirmed outcome."""
    if replication == outcome:
        return (committed + outcome) / 2.0
    return committed


class CrystallizeEvent:
    def __init__(self, pair_seeds, round_no, direction):
        self.pair_seeds = pair_seeds
        self.round_no = round_no
        self.direction = direction
        self.commits = {}
        self.outcome = None
        self.replication = None
        self.replication_reason = None
        self.revised = {}

    def to_dict(self):
        return {
            "pair_seeds": self.pair_seeds,
            "round": self.round_no,
            "direction": self.direction,
            "commits": dict(self.commits),
            "outcome": self.outcome,
            "replication": self.replication,
            "replication_reason": self.replication_reason,
            "revised": dict(self.revised),
        }


class CrystallizeLedger:
    """Hooks for a YinYangPair run: commit, resolve, replicate, revise."""

    def __init__(self, pair, max_events=MAX_EVENTS):
        self.pair = pair
        self.max_events = max_events
        self.events: list[CrystallizeEvent] = []
        self._pending = None
        self._history = {"yin->yang": [], "yang->yin": []}
        # Probe strategy: one initial probe per direction, before the run.
        self._probe_commits = {}
        for direction, source, dest in (
                ("yin->yang", pair.yin, pair.yang),
                ("yang->yin", pair.yang, pair.yin)):
            ok, _reason = pair.wormhole.probe(source, dest)
            self._probe_commits[direction] = 1.0 if ok else 0.0

    def _commit(self, direction):
        history = self._history[direction]
        adaptive = (sum(history) / len(history)) if history else FIRST_COMMIT
        return {
            "fixed": FIRST_COMMIT,
            "probe": self._probe_commits[direction],
            "adaptive": adaptive,
        }

    def before_crossing(self, direction, round_no):
        if len(self.events) >= self.max_events or self._pending is not None:
            return
        event = CrystallizeEvent(
            (self.pair.yin_seed, self.pair.yang_seed), round_no, direction)
        event.commits = self._commit(direction)
        self._pending = event

    def after_crossing(self, record):
        if self._pending is None:
            return
        event = self._pending
        self._pending = None
        if record["reason"] == "receiver_breaker_open":
            return  # Not a guard decision: no event.
        if record["direction"] != event.direction:
            raise AssertionError("ledger direction mismatch")
        event.outcome = 1 if record["accepted"] else 0
        event.replication, event.replication_reason = self._replicate(
            event.direction, event.round_no)
        for strategy in STRATEGIES:
            event.revised[strategy] = revise(
                event.commits[strategy], event.outcome, event.replication)
        self._history[event.direction].append(event.outcome)
        self.events.append(event)

    def _replicate(self, direction, round_no):
        """Reviewer 2: fresh pair, same protocol to round_no - 1, then probe."""
        from .pair import YinYangPair

        yin_seed = self.pair.yin_seed + REPLICATION_SEED_OFFSET
        yang_seed = self.pair.yang_seed + REPLICATION_SEED_OFFSET
        replica = YinYangPair(yin_seed, yang_seed,
                              coupling=self.pair.wormhole.config.coupling)
        for _ in range(round_no - 1):
            replica.run_round(with_wormhole=True)
        if direction == "yin->yang":
            ok, reason = replica.wormhole.probe(replica.yin, replica.yang)
        else:
            ok, reason = replica.wormhole.probe(replica.yang, replica.yin)
        return (1 if ok else 0), reason

    def summary(self):
        """Per-strategy calibration + shared agreement + score."""
        n = len(self.events)
        out = {"n_events": n}
        if n == 0:
            return out
        agreement = sum(1 for e in self.events
                        if e.replication == e.outcome) / n
        out["replication_agreement"] = agreement
        for strategy in STRATEGIES:
            brier_commit = sum(brier(e.commits[strategy], e.outcome)
                               for e in self.events) / n
            brier_revised = sum(brier(e.revised[strategy], e.outcome)
                                for e in self.events) / n
            out[strategy] = {
                "mean_brier_commit": brier_commit,
                "mean_brier_revised": brier_revised,
                "revision_gain": brier_commit - brier_revised,
                "score": (1.0 - brier_revised) - COST_PER_REPLICATION,
            }
        return out


def run_crystallize_pairs(pairs, max_events=MAX_EVENTS):
    """Run pairs with ledgers. Returns (per-pair summaries, pooled events).

    ``pairs`` is a list of (yin_seed, yang_seed). Pooled Brier scores
    are means over ALL events, not means of per-pair means.
    """
    from .pair import YinYangPair

    per_pair = {}
    pooled = []
    for yin_seed, yang_seed in pairs:
        pair = YinYangPair(yin_seed, yang_seed)
        ledger = CrystallizeLedger(pair, max_events=max_events)
        pair.run(with_wormhole=True, hooks=ledger)
        per_pair[(yin_seed, yang_seed)] = ledger.summary()
        pooled.extend(ledger.events)
    n = len(pooled)
    pooled_summary = {"n_events": n}
    if n:
        pooled_summary["replication_agreement"] = sum(
            1 for e in pooled if e.replication == e.outcome) / n
        for strategy in STRATEGIES:
            bc = sum(brier(e.commits[strategy], e.outcome) for e in pooled) / n
            br = sum(brier(e.revised[strategy], e.outcome) for e in pooled) / n
            pooled_summary[strategy] = {
                "mean_brier_commit": bc,
                "mean_brier_revised": br,
                "revision_gain": bc - br,
                "score": (1.0 - br) - COST_PER_REPLICATION,
            }
    return per_pair, pooled_summary
