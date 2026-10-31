"""Crystallize demo: commit, replicate, revise on wormhole crossings.

Pairs: headline (42, 137) + three short-run pairs (1, 1001),
(4, 1004), (7, 1007) — short runs bound replication cost (each
replay runs up to round_no rounds). Runaway pairs are excluded for
the stated cost reason, not hidden: a 200-round replay per event
would make the demo hours long. First 20 events per pair, in order.
Run: python3 demo_crystallize.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wormhole.crystallize import run_crystallize_pairs

PAIRS = [(42, 137), (1, 1001), (4, 1004), (7, 1007)]


def _fmt(summary):
    lines = [f"  n_events={summary['n_events']} "
             f"agreement={summary.get('replication_agreement', float('nan')):.3f}"]
    for strategy in ("fixed", "probe", "adaptive"):
        s = summary.get(strategy)
        if s:
            lines.append(
                f"  {strategy}: brier_commit={s['mean_brier_commit']:.3f} "
                f"brier_revised={s['mean_brier_revised']:.3f} "
                f"gain={s['revision_gain']:.3f} score={s['score']:.3f}")
    return "\n".join(lines)


def main() -> int:
    per_pair, pooled = run_crystallize_pairs(PAIRS)
    for pair, summary in per_pair.items():
        print(f"=== pair {pair} ===")
        print(_fmt(summary))
    print("=== pooled ===")
    print(_fmt(pooled))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
