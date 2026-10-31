"""Bifurcation symmetry in the wormhole: exchange symmetry yin <-> yang.

"Symmetry" here means EXCHANGE symmetry between the two membranes,
not the D4 pattern symmetry of symmetry-quantum-flip-membrane. The
questions, preregistered:
- Q1 (order): does the fixed crossing order (yin -> yang first)
  cause the runaway-direction asymmetry observed at coupling 0.5
  (yin runaway in 9/20 pairs, yang in 2/20)? Prediction: reversing
  the order flips the asymmetry toward yang. Falsifiable either way.
- Q2 (threshold): as coupling rises 0 -> 1, does the fate
  distribution jump at a sharp threshold alpha* (bifurcation) or
  rise smoothly (crossover)? Fate per pair: control-like (both
  latched), yin-runaway, yang-runaway, both-runaway.
- Q3 (asymmetry metric): does the acceptance asymmetry
  (yin -> yang rate minus yang -> yin rate, guard-decided only)
  track the fate, or stay near zero while fates diverge?

Metrics, defined exactly:
- state_distance(A, B) = ||A - B||_F / (||A||_F + ||B||_F): symmetric,
  in [0, 1], 0 for identical states, 1 when one state is zero. This
  is the correlation measurement carried inside the study: distance
  near 0 means the membranes have converged (correlated); distance
  near the independent-pair level means they stayed distinct.
- acceptance_asymmetry: per-direction guard-decided acceptance rates
  (breaker-closed crossings excluded, as in bar 1), difference
  yin -> yang minus yang -> yin.
- fate: from own steps vs max rounds. A membrane that reaches
  max_rounds without latching is a runaway; one that latches earlier
  is not. Full runs use the engine's 200 rounds; proxy sweeps cap
  at 50 rounds and classify fate AT 50 — a defined proxy, not
  claimed identical to fate at 200 (a membrane could in principle
  latch between 50 and 200; the proxy is reported as fate-at-50).

Scope notes, stated openly:
- alpha = 0 is the null control: the mixture equals the destination
  state, so crossings always pass and change nothing.
- alpha = 1 is the known degenerate regime (full replacement,
  source membrane effectively frozen) — included to bound the sweep,
  not as a success case.
- Shared-initialization correlation (yang starting as the conjugate
  mirror of yin) is NOT in this module: it needs reference-aligned
  initialization, not a post-hoc state override (overriding a
  lattice state while its guard reference stays seed-built would
  make the engine's own steps fail for an unrelated reason). It is
  a documented next step, with its design sketched in the README,
  not silently dropped.
"""

from __future__ import annotations

import numpy as np

from .pair import YinYangPair

ALPHAS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)
SWEEP_PAIRS = [(s, s + 1000) for s in range(20)]


def state_distance(state_a, state_b):
    """Symmetric normalized Frobenius distance, in [0, 1]."""
    diff = float(np.linalg.norm(state_a - state_b))
    denom = float(np.linalg.norm(state_a) + np.linalg.norm(state_b))
    if denom == 0.0:
        return 0.0
    return diff / denom


def classify_fate(yin_steps, yang_steps, max_rounds):
    """Fate from own steps vs max rounds."""
    yin_run = yin_steps >= max_rounds
    yang_run = yang_steps >= max_rounds
    if yin_run and yang_run:
        return "both-runaway"
    if yin_run:
        return "yin-runaway"
    if yang_run:
        return "yang-runaway"
    return "control-like"


def direction_rates(crossings):
    """Guard-decided acceptance rates per direction."""
    rates = {}
    for direction in ("yin->yang", "yang->yin"):
        guard = [c for c in crossings
                 if c["direction"] == direction
                 and c["reason"] != "receiver_breaker_open"]
        n = len(guard)
        rates[direction] = (
            sum(1 for c in guard if c["accepted"]) / n) if n else float("nan")
    return rates


def acceptance_asymmetry(crossings):
    """yin -> yang rate minus yang -> yin rate (guard-decided only)."""
    rates = direction_rates(crossings)
    return rates["yin->yang"] - rates["yang->yin"]


def run_with_distances(pair, max_rounds=None):
    """Run a pair round by round, recording state distance per round.

    Returns (summary, distances) where distances[0] is the initial
    distance and distances[k] the distance after round k.
    """
    distances = [state_distance(pair.yin.lattice.state,
                                pair.yang.lattice.state)]
    steps = pair.yin.config.steps
    if max_rounds is not None:
        steps = min(steps, int(max_rounds))
    for _ in range(steps):
        if pair.yin.circuit_breaker and pair.yang.circuit_breaker:
            break
        pair.run_round(with_wormhole=True)
        distances.append(state_distance(pair.yin.lattice.state,
                                        pair.yang.lattice.state))
    return pair.summary(), distances


def sweep_pair(yin_seed, yang_seed, coupling, max_rounds=None,
               crossing_order="yin-first"):
    """One pair at one coupling: fate, asymmetry, distances."""
    pair = YinYangPair(yin_seed, yang_seed, coupling=coupling,
                       crossing_order=crossing_order)
    summary, distances = run_with_distances(pair, max_rounds=max_rounds)
    max_r = max_rounds if max_rounds is not None else pair.yin.config.steps
    return {
        "yin_seed": yin_seed,
        "yang_seed": yang_seed,
        "coupling": coupling,
        "crossing_order": crossing_order,
        "fate": classify_fate(summary["yin_steps"], summary["yang_steps"],
                              max_r),
        "yin_steps": summary["yin_steps"],
        "yin_accepted": summary["yin_accepted"],
        "yang_steps": summary["yang_steps"],
        "yang_accepted": summary["yang_accepted"],
        "asymmetry": acceptance_asymmetry(summary["crossings"]),
        "distance_initial": distances[0],
        "distance_final": distances[-1],
        "distance_mean": sum(distances) / len(distances),
        "n_rounds": len(distances) - 1,
    }


def order_test(pairs=SWEEP_PAIRS, coupling=0.5):
    """Q1: full runs, both crossing orders, same pairs and coupling.

    Returns per-pair fates under both orders plus the runaway counts
    per order and the list of pairs whose fate changed.
    """
    rows = {}
    for yin_seed, yang_seed in pairs:
        row = {}
        for order in ("yin-first", "yang-first"):
            row[order] = sweep_pair(yin_seed, yang_seed, coupling,
                                    max_rounds=None,
                                    crossing_order=order)
        row["fate_changed"] = (row["yin-first"]["fate"]
                               != row["yang-first"]["fate"])
        rows[(yin_seed, yang_seed)] = row
    counts = {}
    for order in ("yin-first", "yang-first"):
        counts[order] = {
            "yin-runaway": sum(1 for r in rows.values()
                               if r[order]["fate"] == "yin-runaway"),
            "yang-runaway": sum(1 for r in rows.values()
                                if r[order]["fate"] == "yang-runaway"),
            "control-like": sum(1 for r in rows.values()
                                if r[order]["fate"] == "control-like"),
            "both-runaway": sum(1 for r in rows.values()
                                if r[order]["fate"] == "both-runaway"),
        }
    changed = [pair for pair, r in rows.items() if r["fate_changed"]]
    return {"rows": rows, "counts": counts, "fate_changed_pairs": changed}


def alpha_sweep(pairs=SWEEP_PAIRS, alphas=ALPHAS, max_rounds=50):
    """Q2/Q3: fate distribution and asymmetry per coupling (proxy 50)."""
    table = {}
    for alpha in alphas:
        rows = [sweep_pair(y, g, alpha, max_rounds=max_rounds)
                for y, g in pairs]
        fates = {}
        for fate in ("control-like", "yin-runaway", "yang-runaway",
                     "both-runaway"):
            fates[fate] = sum(1 for r in rows if r["fate"] == fate)
        asyms = [r["asymmetry"] for r in rows
                 if r["asymmetry"] == r["asymmetry"]]
        dists = [r["distance_final"] for r in rows]
        table[alpha] = {
            "fates": fates,
            "mean_asymmetry": sum(asyms) / len(asyms) if asyms else float("nan"),
            "mean_distance_final": sum(dists) / len(dists),
            "rows": rows,
        }
    return table
