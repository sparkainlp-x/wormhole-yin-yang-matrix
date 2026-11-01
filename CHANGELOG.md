# Changelog

## v0.4.0 (2026-10-31)

- Black-hole and white-hole cells on the wormhole (HoleMap): a black
  cell is a sink (nothing leaves it through the wormhole, it still
  receives), a white cell is a source (nothing enters it through the
  wormhole, it still emits). Holes mask crossing contributions only;
  each engine's own step is untouched, frozen guards still decide
  every crossing, and empty maps reproduce v0.3.0 exactly (pinned by
  test). The names are an analogy for one-way crossing rules in this
  classical toy, NOT astrophysical black/white holes: no event
  horizon, singularity, curvature, or Hawking radiation is modelled.
  See README for the measured bars.


## v0.3.0 (2026-10-31)

- Bifurcation symmetry: crossing-order flag (yin-first default,
  yang-first reversed), fate classification (control-like /
  yin-runaway / yang-runaway / both-runaway), acceptance asymmetry
  (guard-decided only), and symmetric state distance as the
  correlation measurement. Order test (Q1) and coupling sweep (Q2/Q3)
  with a stated fate-at-50 proxy. See README for the measured bars.
  Shared-initialization correlation is a documented next step, not
  silently dropped (it needs reference-aligned initialization).

## v0.2.0 (2026-10-31)

- Crystallize events in the wormhole: commit a probability before
  each guard-decided crossing (fixed 0.35, probe-implied, or adaptive
  running mean), resolve on the crossing outcome, replicate with a
  Reviewer 2 on fresh membranes at the same stage, revise only on
  agreement, scored on calibration minus sampling cost (0.01 per
  replication). Pair runs accept optional hooks; hooks never change
  the pair (pinned by test). See README for the measured bars.

## v0.1.0 (2026-10-31)

- Yin-yang membrane pair inside the 3x3 arena matrix, linked by a
  wormhole: per-cell convex-mixture crossings gated by the receiving
  engine's frozen guards, refused crossings commit nothing, accepted
  crossings logged separately from own steps.
- External observer (REPORTED only, pure-read snapshots) and external
  calibrator (assumed model only, five FailureCapsule reasons).
- Bars measured (seed pairs, held-out probe pairs, calibrator
  scenarios). See README for the numbers.
