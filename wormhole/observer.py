"""External observer for the wormhole pair: measures, never mutates.

Every measurement is tagged REPORTED, never MEASURED. Observation is
pure reads only (state hashes, counters, crossing records the pair
produced anyway). The observer never steps an engine, never transmits,
never commits, never changes a guard or the coupling.

Binary crossing decisions are recorded VERBATIM (no noise added to an
accept/refuse outcome — noise would corrupt the measurement). The
"noise" in a probe is the probe itself (a junk probe is a randomized
candidate). Aggregates carry honest half-widths (binomial for rates).
"""

from __future__ import annotations

import hashlib
import math

import numpy as np

from .pair import YinYangPair

JUNK_SALT = 0x9061


def half_width(values, z=1.96):
    if len(values) < 2:
        return math.inf
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return z * math.sqrt(var / len(values))


def binom_half_width(p, n, z=1.96):
    if n <= 0:
        return math.inf
    return z * math.sqrt(p * (1.0 - p) / n)


class Report:
    def __init__(self, kind, value, half_width=math.inf, n=0, tag="REPORTED"):
        self.kind = kind
        self.value = value
        self.half_width = half_width
        self.n = n
        self.tag = tag

    def to_dict(self):
        return {"kind": self.kind, "value": self.value,
                "half_width": self.half_width, "n": self.n, "tag": self.tag}


class WormholeObserver:
    def __init__(self, pair):
        self.pair = pair
        self.reports = []

    def snapshot(self, engine):
        """Pure read of an engine's observable state. Mutates nothing."""
        return {
            "state_sha256": hashlib.sha256(engine.lattice.state.tobytes()).hexdigest(),
            "step": engine.current_step,
            "failures": engine.failures,
            "breaker": engine.circuit_breaker,
            "n_calibrations": len(engine.calibrations),
            "n_observations": len(engine.observations),
        }

    def crossing_report(self):
        """Aggregate REPORTED report over the pair's crossings so far."""
        guard = [c for c in self.pair.crossings
                 if c["reason"] != "receiver_breaker_open"]
        n = len(guard)
        rate = (sum(1 for c in guard if c["accepted"]) / n) if n else float("nan")
        rep = Report("crossing-aggregate", {"crossing_rate": rate},
                     half_width=binom_half_width(rate, n) if n else math.inf,
                     n=n)
        self.reports.append(rep)
        return rep

    def probe_gate(self, yin_seed, yang_seed):
        """One clean probe and one junk probe on a fresh pair (no stepping).

        Clean probe: the wormhole's mixed present states, validated by
        the receiving guard (no commit — probe() never commits).
        Junk probe: the same mix with the source state replaced by a
        uniform-random complex array of the candidate shape, validated
        by the same guard. Returns (clean_refused, junk_refused,
        clean_reason, junk_reason).
        """
        pair = YinYangPair(yin_seed=yin_seed, yang_seed=yang_seed,
                           coupling=self.pair.wormhole.config.coupling)
        clean_ok, clean_reason = pair.wormhole.probe(pair.yin, pair.yang)
        rng = np.random.default_rng([int(yin_seed), JUNK_SALT])
        shape = pair.yang.lattice.state.shape
        junk = rng.uniform(size=shape) + 1j * rng.uniform(size=shape)
        mixed_junk = pair.wormhole.mix(pair.yang.lattice.state, junk)
        junk_ok, junk_reason = pair.yang._validate(mixed_junk)
        rep = Report("gate", {
            "yin_seed": yin_seed, "yang_seed": yang_seed,
            "clean_refused": not clean_ok,
            "junk_refused": not junk_ok,
            "clean_reason": clean_reason,
            "junk_reason": junk_reason,
        }, half_width=math.inf, n=2)
        self.reports.append(rep)
        return (not clean_ok), (not junk_ok), clean_reason, junk_reason
