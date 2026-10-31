"""Bifurcation demo: Q1 order test (full runs) + Q2/Q3 alpha sweep (proxy 50).

Part 1: 20 pairs at coupling 0.5, full 200-round runs, both crossing
orders — the falsifiable order hypothesis (does reversing the order
flip the yin-runaway asymmetry?).
Part 2: 20 pairs x 6 couplings, fate-at-50 proxy — the bifurcation
diagram (sharp threshold or smooth crossover?).
Part 3: headline pair (42, 137) rows from Parts 1-2.
Run: python3 demo_bifurcation.py (tens of minutes; runaway full runs
dominate Part 1).
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wormhole.bifurcation import (ALPHAS, SWEEP_PAIRS, alpha_sweep,
                                  order_test, sweep_pair)


def _clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _save(path, data):
    with open(path, "w") as fh:
        json.dump(_clean(data), fh, indent=2)


def main() -> int:
    print("=== Q1: order test, coupling 0.5, full runs, 20 pairs ===",
          flush=True)
    result = order_test()
    _save("bifurcation-results-part1.json", {
        "counts": result["counts"],
        "fate_changed_pairs": [list(p) for p in result["fate_changed_pairs"]],
        "fates": {f"{a},{b}": {"yin-first": r["yin-first"]["fate"],
                               "yang-first": r["yang-first"]["fate"]}
                  for (a, b), r in result["rows"].items()},
    })
    for order in ("yin-first", "yang-first"):
        print(f"{order}: {result['counts'][order]}")
    print(f"pairs whose fate changed with order: "
          f"{len(result['fate_changed_pairs'])} {result['fate_changed_pairs']}")
    for pair, row in sorted(result["rows"].items()):
        print(f"  pair {pair}: yin-first={row['yin-first']['fate']} "
              f"yang-first={row['yang-first']['fate']}")
    print("=== Q2/Q3: alpha sweep, fate-at-50 proxy, 20 pairs ===",
          flush=True)
    table = alpha_sweep()
    _save("bifurcation-results-part2.json", {
        str(alpha): {"fates": cell["fates"],
                     "mean_asymmetry": cell["mean_asymmetry"],
                     "mean_distance_final": cell["mean_distance_final"]}
        for alpha, cell in table.items()
    })
    for alpha in ALPHAS:
        cell = table[alpha]
        print(f"alpha {alpha}: fates {cell['fates']} "
              f"mean_asymmetry {cell['mean_asymmetry']:.3f} "
              f"mean_distance_final {cell['mean_distance_final']:.3f}")
    print("=== Headline pair (42, 137), coupling 0.5, full runs ===")
    for order in ("yin-first", "yang-first"):
        row = sweep_pair(42, 137, 0.5, max_rounds=None,
                         crossing_order=order)
        print(f"{order}: fate={row['fate']} "
              f"yin {row['yin_steps']}/{row['yin_accepted']} "
              f"yang {row['yang_steps']}/{row['yang_accepted']} "
              f"asymmetry={row['asymmetry']:.3f} "
              f"distance {row['distance_initial']:.3f} -> "
              f"{row['distance_final']:.3f} (mean {row['distance_mean']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
