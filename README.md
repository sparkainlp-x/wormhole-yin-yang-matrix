# wormhole-yin-yang-matrix v0.4.0

Yin and yang membranes linked by a wormhole inside the 3x3 arena
matrix. The wormhole carries a membrane's PRESENT configuration to
the other side — the yin-yang-membranes motif (yin reads yang's
present, yang reads yin's present), now with the membrane-arena
guards deciding every crossing.

## The mechanism, stated exactly

- **The pair:** two `MembraneArena3x3` engines (yin, yang) with
  frozen stock guards, vendored unchanged (hashes in
  `VENDORED_SHA256.txt`). Each round, each non-broken membrane takes
  one own step, then the wormhole attempts one crossing in each
  direction (yin -> yang, then yang -> yin).
- **The wormhole:** the delivered candidate is a per-cell convex
  mixture of the two lattice states:
  `(1 - coupling) * dest + coupling * source`. A convex mixture of
  density matrices is itself a density matrix per cell, so the
  candidate is always well-formed; whether it crosses is decided
  ONLY by the receiving engine's frozen `_validate` (density
  validity, observation health, parameter bounds).
- **`coupling`** in [0, 1] is a declared channel parameter, frozen
  for a pair: 0 means nothing crosses, 1 means full replacement. It
  is not a physical quantity. No emblackening, traversal-time, or
  collapse dynamics is claimed; each attempt is gated independently
  and there is no latching collapse state.
- **Fail-closed:** a refused crossing commits NOTHING (the receiving
  state is byte-identical afterwards). An accepted crossing commits
  the mixed candidate into the receiving lattice and is logged as a
  crossing record — never as one of the receiving engine's own
  steps. Wormhole commits do not touch failure counters, breakers,
  calibrations, or observations. A crossing into a breaker-open
  membrane is refused as `receiver_breaker_open` without validation,
  and counted separately from guard refusals, never merged into a
  guard rate.
- **Outside the pair:** an external observer records crossing and
  run outcomes as REPORTED (pure reads only, never stepping,
  transmitting, or committing) and an external calibrator updates
  an ASSUMED model only, or refuses with a FailureCapsule. The
  calibrator never changes the coupling or any guard.

## Bars (preregistered) and measured outcome

Bar 1 (measured, demo.py): pair runs with the wormhole vs control
runs without it, same seeds. Headline pair (yin 42, yang 137):
WITH yin 10/5, yang 10/5, crossings 18/18; WITHOUT yin 12/7, yang
10/5 — the wormhole slightly shortened yin's run on this pair.
Means over pairs (yin s, yang s+1000), s in 0-19: WITH yin
95.85/75.40, yang 29.00/22.60, crossing rate 0.980; WITHOUT yin
10.80/5.80, yang 11.10/6.10. Read the mean correctly — the
distribution is BIMODAL, not a uniform extension: median WITH pair
is yin 12 steps, yang 10 steps (essentially the control), while
11/20 pairs develop a runaway membrane that reaches all 200 rounds.
Two runaway modes: frozen (200/200 — the return crossing restores
the membrane's pre-step state, so the same candidate always passes)
and rescued (200 steps with partial acceptance, e.g. 200/71 —
crossings break consecutive-failure streaks so the breaker never
latches). A runaway membrane is a coupling artifact, not better
science: it is either frozen or repeatedly rescued. Per-pair table
in the demo output.

Bar 2a (measured, held-out probe pairs yin 200-299, coupling 0.5):
clean refusal 1.000, junk refusal 1.000, observer path == direct
path. On INITIAL states the frozen gate refuses everything: mixing
two independent lattices drops purity below the guard's floor
(`purity_too_low`), so the gate cannot distinguish clean from junk
at 0.5. Contrast with runs, where post-step mixtures pass at rate
0.980 — probes measure initial-state compatibility, runs measure
converged-pair behaviour, and the two must not be conflated. At weak
coupling 0.1 the gate does discriminate: clean probes pass 30/30,
junk probes are refused (density validity fails for any mixture
containing a non-density junk array). At coupling 1.0 the wormhole
degenerates into state copying (headline: yin 200/200, the loop runs
all 200 rounds, yin effectively frozen) — reported as a degenerate
regime, not a success.

Bar 2b (measured): all five FailureCapsule reasons enumerated
exactly (gate_not_calibrated, review_signoff_missing,
money_gates_failed, too_few_reports, half_width_too_wide).
Applied case: assumed_clean_refusal = 1.0, assumed_junk_refusal =
1.0, frozen gate unchanged, assumed_crossing_rate stays None (the
applied set contained gate reports only). Read the assumed refusals
correctly: they are the INITIAL-state probe result at 0.5, not the
run-crossing result (0.980 accepted).

## Crystallize events in the wormhole (v0.2.0)

Before each guard-decided crossing, commit a probability the guard
will accept it; the crossing resolves the outcome; a simulated
Reviewer 2 replicates the same protocol on fresh membranes at the
same stage (seeds + 5000, same coupling, probe instead of commit);
then revise — but only when replication agrees, halfway toward the
confirmed outcome. Scored on calibration minus sampling cost (0.01
per replication). Commit strategies, per direction: `fixed` 0.35
(the arena injection's first_commit), `probe` (1.0/0.0 from the
pair's initial probe in that direction), `adaptive` (running mean
of past outcomes in that direction, starting at 0.35). Events are
guard-decided crossings only; breaker-closed crossings are not
events. A ledger records at most the first 20 events per pair, in
order — a stated cost bound, since each replication replays up to
round_no rounds. The ledger never touches its pair (pinned by test:
identical crossings with and without hooks).

Bars C1–C3 (measured, demo_crystallize.py; headline + three
short-run pairs, runaway pairs excluded for the stated replay-cost
reason):

- Pooled, 73 events: replication agreement 0.781.
- `fixed`: Brier commit 0.418 → revised 0.171, gain 0.247, score 0.819.
- `probe`: Brier commit 0.986 → revised 0.401, gain 0.586, score 0.589.
- `adaptive`: Brier commit 0.061 → revised 0.060, gain 0.001, score 0.930.

Reading, stated as interpretation: adaptive wins decisively — the
membrane lesson again (track the empirical rate, don't trust a
fixed prior or a probe prior; the probe prior is the worst commit
source for run crossings, because initial-state probes refuse
everything at 0.5 while run crossings pass 98%). Revision rescues
bad priors (probe gain 0.586) and adds nothing to a calibrated one
(adaptive gain 0.001) — that follows from the rule's arithmetic
plus the measured 0.781 agreement, and is reported as such, not as
a discovery. Agreement 0.781 means crossing outcomes are mostly
protocol-determined, partly membrane-specific.

## Bifurcation symmetry (v0.3.0)

Exchange symmetry yin <-> yang, measured — not the D4 pattern
symmetry of symmetry-quantum-flip-membrane. Three preregistered
questions, measured by demo_bifurcation.py (20 pairs, yin s with
yang s+1000, s in 0-19):

- Q1 (order): full 200-round runs at coupling 0.5, both crossing
  orders. yin-first: yin-runaway 9, yang-runaway 2, control-like 9.
  yang-first: yin-runaway 3, yang-runaway 11, control-like 6.
  Fate changed in 12/20 pairs. The prediction is CONFIRMED: reversing
  the order flips the asymmetry. Refined rule: the runaway membrane
  is the one crossed into LAST each round (yin-first ends with
  yang -> yin, so yin runs; yang-first ends with yin -> yang, so
  yang runs). 8 pairs are order-insensitive (2 stay yang-runaway, 3
  stay yin-runaway, 3 stay control-like under both orders) — order
  explains the aggregate flip, not every pair. No both-runaway
  anywhere: at most one membrane runs away.
- Q2 (threshold): fate-at-50 proxy across couplings. Control-like /
  yin-runaway / yang-runaway: 0.0 -> 20/0/0; 0.1 -> 18/2/0;
  0.25 -> 8/7/5; 0.5 -> 9/9/2; 0.75 -> 6/13/1; 1.0 -> 4/15/1.
  No sharp threshold: runaway share rises with coupling (0%, 10%,
  60%, 55%, 70%, 80%) — a crossover, not a bifurcation jump. The
  bifurcation hypothesis (sharp alpha*) is NOT supported. Proxy
  validated at 0.5: fate-at-50 counts (9/9/2) exactly match the
  full-run counts.
- Q3 (asymmetry + distance): mean acceptance asymmetry (yin -> yang
  minus yang -> yin, guard-decided only) goes 0.000, 0.044, -0.024,
  -0.139, -0.349, -0.404 across couplings 0.0-1.0 — it tracks the
  fate (near zero where fates are balanced at 0.25, increasingly
  negative as yin-runaway dominates). Mean final state distance
  collapses with coupling: 0.499, 0.086, 0.019, 0.011, 0.007, 0.000.
  Membranes converge at every coupling above 0 (already to 0.086
  at 0.1); at 0.0 they stay distinct (0.499, null control
  validated). Headline pair (42, 137) at 0.5 stays control-like
  under both orders (10/5 vs 9/4 steps) yet converges fully
  (distance 0.497 -> 0.000) — convergence is not runaway.

## Black holes and white holes (v0.4.0)

One-way crossing rules, added as a `HoleMap` per engine. The names
are an analogy, not astrophysics: no event horizon, singularity,
curvature, or Hawking radiation is modelled, and no claim about real
black or white holes is made.

- A BLACK cell is a sink: nothing leaves it through the wormhole
  (its contribution to an outgoing crossing is zeroed; the
  destination keeps its own cell there). It still RECEIVES normally,
  subject to the frozen guards: a sink absorbs.
- A WHITE cell is a source: nothing enters it through the wormhole
  (an incoming contribution to it is zeroed; the destination keeps
  its own cell there). It still EMITS normally: a source only gives.
- Holes mask crossing contributions only. Each engine's own step is
  untouched, frozen guards still decide every crossing, and a refused
  crossing still commits nothing. A cell cannot be both black and
  white; off-grid cells are rejected. Empty maps reproduce v0.3.0
  exactly (pinned by test).

Measured by demo_holes.py:

- Part 1 (mechanism trace, headline pair 42/137, coupling 0.5):
  per-cell ||candidate - dest|| for a yin -> yang crossing. Plain:
  every cell moves by about 0.12. With a black hole on yin at
  (1, 1), or a white hole on yang at (1, 1), the (1, 1) cell reads
  exactly 0.0000 and every other cell is unchanged.
- Part 2 (fate-at-50 proxy, 10 pairs s in 0-9, coupling 0.5,
  yin-first; control-like / yin-runaway / yang-runaway): no holes
  6/2/2, mean final distance 0.006; black on yin (1, 1) 7/2/1,
  mean 0.027; white on yang (1, 1) 7/2/1, mean 0.027. No
  both-runaway anywhere. One yang-runaway pair turns control-like
  under either hole; yin-runaway is unchanged. Small sample (10
  pairs): read this as a measured hint, not a law.
- The two single-hole conditions agree EXACTLY here, and that is
  structural, not coincidence: each masks the same (1, 1) cell of
  the yin -> yang candidate, and neither masks the yang -> yin
  candidate at all (black blocks only leaving, white blocks only
  entering). Identical crossings give identical trajectories.
  Holes slightly slow convergence (mean final distance 0.006 ->
  0.027): one masked cell per direction keeps the membranes a
  little more distinct.

## Run it

```sh
python3 demo.py            # bar 1, bar 2, calibrator scenarios, coupling sensitivity
python3 demo_crystallize.py  # bars C1-C3 (4 pairs, first 20 events each)
python3 demo_bifurcation.py  # Q1 order test + Q2/Q3 alpha sweep (tens of minutes)
python3 demo_holes.py      # hole trace + fate-at-50 with black/white holes (minutes)
python3 tests/tests.py     # 11 tests, from the package root
python3 tests/test_crystallize.py  # 5 tests, from the package root
python3 tests/test_bifurcation.py  # 6 tests, from the package root
python3 tests/test_holes.py  # 13 tests, from the package root
```

Tests pin the mechanism (refused crossings commit nothing, accepted
crossings commit validated mixtures, observer non-mutation,
determinism, frozen gate, gate-path agreement, calibrator gate
logic, vendored bytes, NumPy declaration; crystallize arithmetic,
per-direction adaptive history, ledger non-interference, replication
determinism, score arithmetic; hole validation, mask placement,
black-receives / white-emits, guard refusal with holes, holes inert
without the wormhole, empty maps reproducing v0.3.0). Full bar 1
(21 pairs) and bar 2 (100 probe pairs) numbers are measured by
demo.py and reported above, not re-run in the tests, so the suite
stays fast.

## Honest limits

- **NumPy, declared:** this package is NOT stdlib-only. The vendored
  arena engine uses NumPy throughout, and `pyproject.toml` declares
  numpy as a dependency. No stdlib port: a port would change
  `np.random.default_rng` trajectories and break comparability with
  the arena's own measured numbers.
- **The wormhole is a declared coupling, not physics.** The
  micro-wormhole network of the island-formula work remains
  conjecture; nothing here validates traversable wormholes, and no
  collapse, traversal-time, or emblackening claim is made.
- **Binary decisions recorded verbatim:** the observer adds no noise
  to an accept/refuse outcome. Aggregates carry honest half-widths
  (binomial for rates).
- **Classical synthetic toy only.** No biology, medical, quantum,
  brain, or consciousness claim. Both membranes still latch their
  breakers; the wormhole does not cure the arena.
- **The calibrator's assumed model is not the system.** An applied
  calibration changes what the outside world believes, never a
  guard, a threshold, or the coupling.

## Licence

AGPL-3.0-only. See `LICENSE`.
