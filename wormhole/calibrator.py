"""External calibrator: updates ASSUMED parameters only, or refuses.

Fail-closed gates, in the same order as bubble-nervous-system and
bubble-arena-injection:
 1. gate_not_calibrated / review_signoff_missing / money_gates_failed
 2. too_few_reports (fewer than 3 reports)
 3. half_width_too_wide (any report half-width >= 0.20)
Otherwise estimates come from REPORTED values only, never from true
engine parameters. Applying a calibration updates the pair's ASSUMED
model only. The frozen guards and the wormhole coupling are never
overwritten.
"""

from __future__ import annotations


class FailureCapsule:
    def __init__(self, reason, detail=None):
        self.reason = reason
        self.detail = detail or {}

    def to_dict(self):
        return {"refused": True, "reason": self.reason, "detail": self.detail}


class WormholeCalibrator:
    def __init__(self, pair):
        self.pair = pair

    def _gate_check(self, reports):
        if not self.pair.gates.get("gate_calibrated"):
            return FailureCapsule("gate_not_calibrated")
        if not self.pair.gates.get("review_signoff"):
            return FailureCapsule("review_signoff_missing")
        if not self.pair.gates.get("money_gates_pass"):
            return FailureCapsule("money_gates_failed")
        if len(reports) < 3:
            return FailureCapsule("too_few_reports", {"n": len(reports)})
        for r in reports:
            if r.half_width is not None and r.half_width >= 0.20:
                return FailureCapsule("half_width_too_wide",
                                      {"kind": r.kind, "half_width": r.half_width})
        return None

    def calibrate(self, reports):
        """Return (applied_dict, capsule_or_None)."""
        fail = self._gate_check(reports)
        if fail is not None:
            return None, fail
        out = {}
        cross_reps = [r for r in reports if r.kind == "crossing-aggregate"]
        rates = [r.value["crossing_rate"] for r in cross_reps
                 if r.value["crossing_rate"] == r.value["crossing_rate"]]
        if rates:
            out["assumed_crossing_rate"] = sum(rates) / len(rates)
        gate_reps = [r for r in reports if r.kind == "gate-aggregate"]
        clean_vals = [r.value["clean_refusal_rate"] for r in gate_reps
                      if "clean_refusal_rate" in r.value]
        junk_vals = [r.value["junk_refusal_rate"] for r in gate_reps
                     if "junk_refusal_rate" in r.value]
        if clean_vals:
            out["assumed_clean_refusal"] = sum(clean_vals) / len(clean_vals)
        if junk_vals:
            out["assumed_junk_refusal"] = sum(junk_vals) / len(junk_vals)
        return out, None

    def apply(self, calibration):
        """Apply to the assumed model only. Never touches engines or wormhole."""
        if calibration is None:
            return False
        for key, value in calibration.items():
            setattr(self.pair, key, value)
        return True
