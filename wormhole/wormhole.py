"""Wormhole channel between the yin and yang membranes.

The wormhole carries a membrane's PRESENT configuration to the other
side — the yin-yang-membranes motif (yin reads yang's present, yang
reads yin's present), now inside the 3x3 density-matrix lattice.

Mechanism, stated exactly (no invented physics):
- The delivered candidate is a per-cell convex mixture of the two
  lattice states: ``(1 - coupling) * dest + coupling * source``.
  A convex mixture of density matrices is itself a density matrix
  per cell, so the mixture is always a well-formed candidate; whether
  it crosses is decided ONLY by the receiving engine's frozen guards
  (its own ``_validate``: density validity, observation health,
  parameter bounds).
- ``coupling`` in [0, 1] is a declared channel parameter, frozen for
  a pair: 0 means nothing crosses, 1 means full replacement. It is
  not a physical quantity and no emblackening, traversal-time, or
  collapse dynamics is claimed. Each attempt is gated independently;
  there is no latching collapse state.
- A refused crossing commits NOTHING: the receiving state is
  byte-identical afterwards. An accepted crossing commits the mixed
  candidate into the receiving lattice (``lattice.commit``) and is
  logged as a crossing record — never as one of the receiving
  engine's own steps. Wormhole commits do not touch the receiving
  engine's failure counter, breaker, calibrations, or observations.
- A crossing into a breaker-open membrane is refused with reason
  ``receiver_breaker_open`` without validation: the wormhole is
  closed to a broken membrane. Such refusals are counted separately
  from guard refusals, never merged into a guard rate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WormholeConfig:
    """Declared channel parameters. Frozen for a pair."""

    coupling: float = 0.5  # convex-mixture weight of the source state

    def __post_init__(self) -> None:
        if not 0.0 <= self.coupling <= 1.0:
            raise ValueError("coupling must be in [0, 1]")


class Wormhole:
    """Stateless gated channel between two arena engines."""

    def __init__(self, config: WormholeConfig | None = None):
        self.config = config or WormholeConfig()

    def mix(self, dest_state, source_state):
        """Per-cell convex mixture. Preserves density-matrix validity."""
        alpha = self.config.coupling
        return (1.0 - alpha) * dest_state + alpha * source_state

    def probe(self, source_engine, dest_engine, candidate=None):
        """Validate a crossing WITHOUT committing. Returns (ok, reason).

        ``candidate`` defaults to the mixed present states. Probes never
        mutate either engine (validation is pure).
        """
        if dest_engine.circuit_breaker:
            return False, "receiver_breaker_open"
        if candidate is None:
            candidate = self.mix(dest_engine.lattice.state,
                                 source_engine.lattice.state)
        return dest_engine._validate(candidate)

    def transmit(self, source_engine, dest_engine, direction, round_no):
        """Attempt one crossing. Commits only a validated candidate.

        Returns a crossing record dict (direction, round, accepted,
        reason). Refused attempts leave the receiving state untouched.
        """
        if dest_engine.circuit_breaker:
            record = {"direction": direction, "round": round_no,
                      "accepted": False, "reason": "receiver_breaker_open"}
            return record
        candidate = self.mix(dest_engine.lattice.state,
                             source_engine.lattice.state)
        ok, reason = dest_engine._validate(candidate)
        if ok:
            dest_engine.lattice.commit(candidate)
        record = {"direction": direction, "round": round_no,
                  "accepted": bool(ok), "reason": reason}
        return record
