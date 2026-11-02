"""Demo: triangle hole patterns in the wormhole.

Part 1 (mechanism trace, headline pair 42/137, coupling 0.5): the
per-cell Frobenius norm of (candidate - dest) for a plain crossing,
a crossing with the black triangle on yin, and a crossing with the
white triangle on yang. Triangle cells read exactly 0.0000: the
contribution never crosses there. Everything else is unchanged.

Part 2 (fate-at-50 proxy, pairs s in 0..9, coupling 0.5, yin-first):
fate counts with no holes, with the black triangle on yin, with
the white triangle on yang, and with the black triangle on BOTH
engines (both crossing directions masked). The black-on-yin and
white-on-yang conditions are predicted to agree EXACTLY (same
candidate cells masked, same direction) -- a structural prediction,
checked here, not a fitted result. The both-directions condition
carries no beforehand claim: whatever fate shift appears is
measured here. Fate-at-50 is the same proxy as the bifurcation
study (a membrane could in principle latch between 50 and 200
rounds).

Run from the package root: python3 demo_triangles.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from wormhole.bifurcation import classify_fate, run_with_distances  # noqa: E402
from wormhole.pair import YinYangPair  # noqa: E402
from wormhole.triangles import (  # noqa: E402
    TRIANGLE_CELLS, triangle_black, triangle_white)


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
        source_black=triangle_black().source_mask())
    white = pair.wormhole.mix(
        dest, src,
        dest_white=triangle_white().dest_mask())
    print(f"Part 1: per-cell ||candidate - dest||_F, yin->yang, "
          f"seeds 42/137, triangle {sorted(TRIANGLE_CELLS)}")
    for name, cand in (("plain", plain),
                       ("black triangle on yin", black),
                       ("white triangle on yang", white)):
        print(f"  {name}:")
        for row in _cell_norms(cand, dest):
            print("    " + " ".join(f"{v:.4f}" for v in row))


def part2_fates():
    pairs = [(s, s + 1000) for s in range(10)]
    conditions = (
        ("no holes", None, None),
        ("black triangle on yin", triangle_black(), None),
        ("white triangle on yang", None, triangle_white()),
        ("black triangle on both", triangle_black(), triangle_black()),
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
