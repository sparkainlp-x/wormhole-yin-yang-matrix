"""Demo: black-hole and white-hole cells in the wormhole.

Part 1 (mechanism trace, headline pair 42/137, coupling 0.5): the
per-cell Frobenius norm of (candidate - dest) for a plain crossing,
a crossing with a black hole on yin at (1, 1), and a crossing with a
white hole on yang at (1, 1). Masked cells read exactly 0.0000: the
contribution never crosses there. Everything else is unchanged.

Part 2 (fate-at-50 proxy, pairs s in 0..9, coupling 0.5, yin-first):
fate counts with no holes, with a black hole on yin at (1, 1), and
with a white hole on yang at (1, 1). No directional claim is made
beforehand: holes only mask crossing contributions, and whatever
fate shift appears is measured here, not asserted. Fate-at-50 is the
same proxy as the bifurcation study (a membrane could in principle
latch between 50 and 200 rounds).

Run from the package root: python3 demo_holes.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from wormhole.bifurcation import classify_fate, run_with_distances  # noqa: E402
from wormhole.holes import HoleMap  # noqa: E402
from wormhole.pair import YinYangPair  # noqa: E402


def _cell_norms(candidate, dest):
    """Per-cell ||candidate - dest||_F on the 3x3 grid."""
    return [[float(np.linalg.norm(candidate[r, c] - dest[r, c]))
             for c in range(3)] for r in range(3)]


def part1_trace():
    pair = YinYangPair(42, 137)
    dest = pair.yang.lattice.state.copy()
    src = pair.yin.lattice.state.copy()
    plain = pair.wormhole.mix(dest, src)
    black = pair.wormhole.mix(
        dest, src,
        source_black=HoleMap(black=[(1, 1)]).source_mask())
    white = pair.wormhole.mix(
        dest, src,
        dest_white=HoleMap(white=[(1, 1)]).dest_mask())
    print("Part 1: per-cell ||candidate - dest||_F, yin->yang, seeds 42/137")
    for name, cand in (("plain", plain), ("black on yin (1,1)", black),
                       ("white on yang (1,1)", white)):
        print(f"  {name}:")
        for row in _cell_norms(cand, dest):
            print("    " + " ".join(f"{v:.4f}" for v in row))


def part2_fates():
    pairs = [(s, s + 1000) for s in range(10)]
    conditions = (
        ("no holes", None, None),
        ("black on yin (1,1)", HoleMap(black=[(1, 1)]), None),
        ("white on yang (1,1)", None, HoleMap(white=[(1, 1)])),
    )
    print("Part 2: fate-at-50, 10 pairs, coupling 0.5, yin-first")
    for name, yin_holes, yang_holes in conditions:
        fates = {}
        finals = []
        for yin_seed, yang_seed in pairs:
            pair = YinYangPair(yin_seed, yang_seed, coupling=0.5,
                               yin_holes=yin_holes, yang_holes=yang_holes)
            summary, distances = run_with_distances(pair, max_rounds=50)
            fate = classify_fate(summary["yin_steps"],
                                 summary["yang_steps"], 50)
            fates[fate] = fates.get(fate, 0) + 1
            finals.append(distances[-1])
        counts = " ".join(f"{k} {fates.get(k, 0)}"
                          for k in ("control-like", "yin-runaway",
                                    "yang-runaway", "both-runaway"))
        print(f"  {name}: {counts} | mean final distance "
              f"{sum(finals) / len(finals):.3f}")


def main():
    part1_trace()
    part2_fates()


if __name__ == "__main__":
    main()
