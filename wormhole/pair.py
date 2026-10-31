"""Yin-yang membrane pair inside the 3x3 arena matrix.

Two MembraneArena3x3 engines (yin, yang) with frozen stock guards,
linked by one Wormhole. Each round: each non-broken membrane takes
one own step, then the wormhole attempts one crossing in each
direction (yin -> yang, then yang -> yin). The run stops when both
breakers are open or the requested rounds are exhausted.

What the wormhole does and does not do:
- It commits ONLY validated mixed candidates, and only into the
  receiving lattice. It never changes a guard, a threshold, a
  failure counter, a breaker, or either engine's own step log.
- Engine summaries count own steps only. Crossings are counted
  separately in ``pair.crossings`` and in the pair summary.
- The control run (``with_wormhole=False``) steps the same seeds
  with no transmits: the baseline the coupling effect is measured
  against. Any with-vs-without difference is the coupling effect,
  reported, not tuned away.
"""

from __future__ import annotations

from membrane_arena_3x3.engine import EngineConfig, MembraneArena3x3

from .wormhole import Wormhole, WormholeConfig


class YinYangPair:
    """Two arena membranes + one wormhole + an assumed model."""

    def __init__(self, yin_seed=42, yang_seed=137, coupling=0.5, steps=200,
                 crossing_order="yin-first"):
        if crossing_order not in ("yin-first", "yang-first"):
            raise ValueError(
                "crossing_order must be 'yin-first' or 'yang-first'")
        self.yin_seed = int(yin_seed)
        self.yang_seed = int(yang_seed)
        self.crossing_order = crossing_order
        self.yin = MembraneArena3x3(
            EngineConfig(steps=int(steps), seed=self.yin_seed))
        self.yang = MembraneArena3x3(
            EngineConfig(steps=int(steps), seed=self.yang_seed))
        self.wormhole = Wormhole(WormholeConfig(coupling=coupling))
        self.crossings: list[dict] = []
        self.rounds_run = 0
        # Calibration gates (fail-closed, as in bubble-nervous-system).
        self.gates = {
            "gate_calibrated": True,
            "review_signoff": False,
            "money_gates_pass": True,
        }
        # Assumed model: outside beliefs, None until a calibration applies.
        self.assumed_crossing_rate = None
        self.assumed_clean_refusal = None
        self.assumed_junk_refusal = None

    def set_review_signoff(self, value=True):
        self.gates["review_signoff"] = bool(value)

    def frozen_gate(self):
        """Frozen guards + coupling + crossing order (read-only view)."""
        probe = MembraneArena3x3(EngineConfig(steps=200, seed=42))
        return {
            "guards": dict(probe.config.guards_dict()),
            "coupling": self.wormhole.config.coupling,
            "crossing_order": self.crossing_order,
        }

    def public_state(self):
        """What the outside world may see: assumed model only."""
        return {
            "assumed_crossing_rate": self.assumed_crossing_rate,
            "assumed_clean_refusal": self.assumed_clean_refusal,
            "assumed_junk_refusal": self.assumed_junk_refusal,
            "gate_frozen": True,
        }

    def run_round(self, with_wormhole=True, hooks=None):
        """One round: own steps, then one crossing each direction.

        ``hooks`` (optional) is an observer with ``before_crossing``
        and ``after_crossing`` methods (see CrystallizeLedger). Hooks
        never change the pair: they observe records only, and any
        work they do runs on separate pairs, never this one.
        """
        if not self.yin.circuit_breaker:
            self.yin.step()
        if not self.yang.circuit_breaker:
            self.yang.step()
        if with_wormhole:
            order = (("yin->yang", self.yin, self.yang),
                     ("yang->yin", self.yang, self.yin))
            if self.crossing_order == "yang-first":
                order = order[::-1]
            for direction, source, dest in order:
                if hooks is not None:
                    hooks.before_crossing(direction, self.rounds_run + 1)
                record = self.wormhole.transmit(
                    source, dest, direction, self.rounds_run + 1)
                self.crossings.append(record)
                if hooks is not None:
                    hooks.after_crossing(record)
        self.rounds_run += 1

    def run(self, with_wormhole=True, hooks=None, max_rounds=None):
        """Run until both breakers open or steps are exhausted.

        ``max_rounds`` caps the loop (bifurcation proxy sweeps use 50
        instead of the engine's 200; None means the engine's steps).
        """
        steps = self.yin.config.steps
        if max_rounds is not None:
            steps = min(steps, int(max_rounds))
        for _ in range(steps):
            if self.yin.circuit_breaker and self.yang.circuit_breaker:
                break
            self.run_round(with_wormhole=with_wormhole, hooks=hooks)
        return self.summary()

    def summary(self):
        """Own-step summaries + crossing counts (kept separate)."""
        yin = self.yin.summary()
        yang = self.yang.summary()
        guard_crossings = [c for c in self.crossings
                           if c["reason"] != "receiver_breaker_open"]
        accepted = sum(1 for c in guard_crossings if c["accepted"])
        return {
            "yin_steps": yin["steps_executed"],
            "yin_accepted": yin["accepted_steps"],
            "yin_status": yin["status"],
            "yang_steps": yang["steps_executed"],
            "yang_accepted": yang["accepted_steps"],
            "yang_status": yang["status"],
            "rounds": self.rounds_run,
            "crossings_attempted": len(self.crossings),
            "crossings_guard_decided": len(guard_crossings),
            "crossings_accepted": accepted,
            "crossings_breaker_closed": (
                len(self.crossings) - len(guard_crossings)),
            "crossings": list(self.crossings),
        }
