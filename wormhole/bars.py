"""Preregistered bars for wormhole-yin-yang-matrix. Measure both, tune neither.

Bar 1: pair runs with the wormhole vs control runs without it, same
seeds: own steps/accepted per membrane, crossing attempts, guard
decisions, acceptances. Headline pair (yin 42, yang 137) plus pairs
(yin s, yang s+1000) for s in 0-19. Any with-vs-without difference is
the coupling effect, reported, not tuned away.

Bar 2a: frozen-gate refusal rates through the wormhole, clean vs
junk, on held-out probe pairs (yin 200-299, yang = yin+1000),
measured through the observer and directly — reported SEPARATELY,
never merged. Clean probe: mixed present states, validated, never
committed. Junk probe: the same mix with the source state replaced
by a uniform-random complex array, validated by the same guard.

Bar 2b: calibrator FailureCapsule refusals BY REASON, enumerated by
scenario — also reported separately from 2a, never merged into one
rate. The gate is frozen: stock GuardConfig thresholds plus the
pair's coupling, never re-tuned on held-out probes.
"""

from __future__ import annotations

import math

import numpy as np

from .calibrator import WormholeCalibrator
from .observer import JUNK_SALT, Report, binom_half_width
from .pair import YinYangPair

BAR1_PAIRS = [(42, 137)] + [(s, s + 1000) for s in range(20)]
BAR2_YIN_SEEDS = list(range(200, 300))


def _mean(values):
    return sum(values) / len(values) if values else float("nan")


def _pair_summary(pair):
    s = pair.summary()
    guard = s["crossings_guard_decided"]
    rate = (s["crossings_accepted"] / guard) if guard else float("nan")
    return {
        "yin_steps": s["yin_steps"],
        "yin_accepted": s["yin_accepted"],
        "yang_steps": s["yang_steps"],
        "yang_accepted": s["yang_accepted"],
        "crossings_attempted": s["crossings_attempted"],
        "crossings_guard_decided": guard,
        "crossings_accepted": s["crossings_accepted"],
        "crossing_rate": rate,
        "breaker_closed": s["crossings_breaker_closed"],
    }


def bar1(coupling=0.5):
    """With-wormhole vs control runs for every bar-1 pair."""
    table = {}
    for yin_seed, yang_seed in BAR1_PAIRS:
        with_pair = YinYangPair(yin_seed, yang_seed, coupling=coupling)
        with_pair.run(with_wormhole=True)
        control = YinYangPair(yin_seed, yang_seed, coupling=coupling)
        control.run(with_wormhole=False)
        table[(yin_seed, yang_seed)] = {
            "with": _pair_summary(with_pair),
            "without": _pair_summary(control),
        }
    means = {}
    for key in ("with", "without"):
        cells = [table[(s, s + 1000)][key] for s in range(20)]
        means[key] = {
            "mean_yin_steps": _mean([c["yin_steps"] for c in cells]),
            "mean_yin_accepted": _mean([c["yin_accepted"] for c in cells]),
            "mean_yang_steps": _mean([c["yang_steps"] for c in cells]),
            "mean_yang_accepted": _mean([c["yang_accepted"] for c in cells]),
            "mean_crossing_rate": _mean([c["crossing_rate"] for c in cells
                                         if c["crossing_rate"] == c["crossing_rate"]]),
        }
    return table, means


def bar2_rates(observer):
    """Frozen-gate refusal rates, observer path and direct path."""
    clean_obs, junk_obs, clean_dir, junk_dir = [], [], [], []
    for yin_seed in BAR2_YIN_SEEDS:
        yang_seed = yin_seed + 1000
        clean_ref, junk_ref, _cr, _jr = observer.probe_gate(yin_seed, yang_seed)
        clean_obs.append(clean_ref)
        junk_obs.append(junk_ref)
        pair = YinYangPair(yin_seed, yang_seed,
                           coupling=observer.pair.wormhole.config.coupling)
        clean_ok, _r = pair.wormhole.probe(pair.yin, pair.yang)
        rng = np.random.default_rng([int(yin_seed), JUNK_SALT])
        shape = pair.yang.lattice.state.shape
        junk = rng.uniform(size=shape) + 1j * rng.uniform(size=shape)
        mixed_junk = pair.wormhole.mix(pair.yang.lattice.state, junk)
        junk_ok, _r2 = pair.yang._validate(mixed_junk)
        clean_dir.append(not clean_ok)
        junk_dir.append(not junk_ok)
    n = len(BAR2_YIN_SEEDS)
    return {
        "n_pairs": n,
        "clean_refusal_observer": _mean([1.0 if v else 0.0 for v in clean_obs]),
        "junk_refusal_observer": _mean([1.0 if v else 0.0 for v in junk_obs]),
        "clean_refusal_direct": _mean([1.0 if v else 0.0 for v in clean_dir]),
        "junk_refusal_direct": _mean([1.0 if v else 0.0 for v in junk_dir]),
        "observer_equals_direct": clean_obs == clean_dir and junk_obs == junk_dir,
    }


def gate_aggregate_reports(observer, path="observer"):
    """Aggregate gate reports over BAR2_YIN_SEEDS, one per (path, probe type)."""
    if path == "observer":
        clean = [observer.probe_gate(s, s + 1000)[0] for s in BAR2_YIN_SEEDS]
        junk = [observer.probe_gate(s, s + 1000)[1] for s in BAR2_YIN_SEEDS]
    else:
        clean, junk = [], []
        for yin_seed in BAR2_YIN_SEEDS:
            pair = YinYangPair(yin_seed, yin_seed + 1000,
                               coupling=observer.pair.wormhole.config.coupling)
            clean_ok, _r = pair.wormhole.probe(pair.yin, pair.yang)
            rng = np.random.default_rng([int(yin_seed), JUNK_SALT])
            shape = pair.yang.lattice.state.shape
            junk_arr = rng.uniform(size=shape) + 1j * rng.uniform(size=shape)
            mixed_junk = pair.wormhole.mix(pair.yang.lattice.state, junk_arr)
            junk_ok, _r2 = pair.yang._validate(mixed_junk)
            clean.append(not clean_ok)
            junk.append(not junk_ok)
    n = len(BAR2_YIN_SEEDS)
    reports = []
    for kind, vals in (("clean", clean), ("junk", junk)):
        p = _mean([1.0 if v else 0.0 for v in vals])
        reports.append(Report("gate-aggregate",
                              {f"{kind}_refusal_rate": p},
                              half_width=binom_half_width(p, n), n=n))
    return reports


def calibrator_scenarios(pair, observer):
    """Enumerate FailureCapsule refusals by reason, plus one applied case.

    Scenarios 1-3 use real gate-aggregate reports. The money case sets
    signoff True first (the gate returns the FIRST failure in order,
    so an unset signoff would mask it). The half-width case is a
    labeled gate-logic check (one report's half-width inflated to
    0.25). The applied case uses four real aggregate reports
    (observer x direct, clean x junk) and applies only if every
    half-width is < 0.20.
    """
    cal = WormholeCalibrator(pair)
    real_reports = gate_aggregate_reports(observer, "observer")
    applied_reports = real_reports + gate_aggregate_reports(observer, "direct")
    out = []
    saved = dict(pair.gates)
    pair.gates["gate_calibrated"] = False
    _v, cap = cal.calibrate(applied_reports)
    out.append(("gate_not_calibrated", cap.reason if cap else "APPLIED-UNEXPECTED"))
    pair.gates.update(saved)
    pair.gates["review_signoff"] = False
    _v, cap = cal.calibrate(applied_reports)
    out.append(("review_signoff_missing", cap.reason if cap else "APPLIED-UNEXPECTED"))
    pair.set_review_signoff(True)
    pair.gates["money_gates_pass"] = False
    _v, cap = cal.calibrate(applied_reports)
    out.append(("money_gates_failed", cap.reason if cap else "APPLIED-UNEXPECTED"))
    pair.gates.update(saved)
    pair.set_review_signoff(True)
    _v, cap = cal.calibrate(applied_reports[:2])
    out.append(("too_few_reports", cap.reason if cap else "APPLIED-UNEXPECTED"))
    inflated = list(applied_reports)
    inflated[0] = Report(inflated[0].kind, inflated[0].value,
                         half_width=0.25, n=inflated[0].n)
    _v, cap = cal.calibrate(inflated)
    out.append(("half_width_too_wide_gate_logic_check",
                cap.reason if cap else "APPLIED-UNEXPECTED"))
    before_gate = pair.frozen_gate()
    applied, cap = cal.calibrate(applied_reports)
    if cap is not None:
        out.append(("applied_case", f"REFUSED:{cap.reason}"))
    else:
        cal.apply(applied)
        out.append(("applied_case", {
            "assumed": applied,
            "frozen_gate_unchanged": before_gate == pair.frozen_gate(),
            "public_state": pair.public_state(),
        }))
    pair.gates.update(saved)
    pair.set_review_signoff(False)
    return out
