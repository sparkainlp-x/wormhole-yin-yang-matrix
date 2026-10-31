"""Demo: bar 1, bar 2, calibrator scenarios, coupling sensitivity. Run: python3 demo.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wormhole.bars import bar1, bar2_rates, calibrator_scenarios
from wormhole.observer import WormholeObserver
from wormhole.pair import YinYangPair


def main() -> int:
    print("=== Bar 1: with wormhole vs control (same seeds) ===")
    table, means = bar1()
    head = table[(42, 137)]
    print(f"headline (42,137) WITH: yin {head['with']['yin_steps']}/{head['with']['yin_accepted']} "
          f"yang {head['with']['yang_steps']}/{head['with']['yang_accepted']} "
          f"crossings {head['with']['crossings_accepted']}/{head['with']['crossings_guard_decided']}")
    print(f"headline (42,137) WITHOUT: yin {head['without']['yin_steps']}/{head['without']['yin_accepted']} "
          f"yang {head['without']['yang_steps']}/{head['without']['yang_accepted']}")
    for key in ("with", "without"):
        m = means[key]
        print(f"mean(0-19) {key}: yin {m['mean_yin_steps']:.2f}/{m['mean_yin_accepted']:.2f} "
              f"yang {m['mean_yang_steps']:.2f}/{m['mean_yang_accepted']:.2f} "
              f"crossing_rate {m['mean_crossing_rate']:.3f}")
    print("=== Coupling sensitivity (headline pair only) ===")
    for coupling in (0.25, 0.5, 1.0):
        pair = YinYangPair(42, 137, coupling=coupling)
        s = pair.run(with_wormhole=True)
        guard = s["crossings_guard_decided"]
        rate = (s["crossings_accepted"] / guard) if guard else float("nan")
        print(f"coupling {coupling}: crossings {s['crossings_accepted']}/{guard} rate {rate:.3f}")
    print("=== Bar 2a: frozen-gate refusal rates, held-out probe pairs 200-299 ===")
    observer = WormholeObserver(YinYangPair(42, 137))
    rates = bar2_rates(observer)
    print(f"n_pairs={rates['n_pairs']} "
          f"clean(observer)={rates['clean_refusal_observer']:.3f} "
          f"junk(observer)={rates['junk_refusal_observer']:.3f} "
          f"clean(direct)={rates['clean_refusal_direct']:.3f} "
          f"junk(direct)={rates['junk_refusal_direct']:.3f} "
          f"observer_equals_direct={rates['observer_equals_direct']}")
    print("=== Bar 2b: calibrator refusals by reason (separate from 2a) ===")
    pair = YinYangPair(42, 137)
    observer2 = WormholeObserver(pair)
    for name, outcome in calibrator_scenarios(pair, observer2):
        print(f"{name}: {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
