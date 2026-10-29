"""Experimental outcome-calibrated sensor trust with strictly delayed feedback.

A source's Beta reliability estimate is updated only when the host reveals
an outcome AFTER its prediction was recorded. Evidence identities are checked,
source names are assertions, and outcomes are host attested, not authenticated.
No BEAN Core policy or weights are changed by this module.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SensorObservation:
    evidence_id: str
    origin: str
    value: int


class OnlineSensorTrust:
    """Binary naive Bayes with optionally decayed source-specific Beta weights."""

    def __init__(self, *, alpha=3.0, beta=1.0, decay=1.0, max_log_odds=12.0):
        if any(type(x) not in (int, float) or not math.isfinite(x)
               for x in (alpha, beta, decay, max_log_odds)):
            raise ValueError("non-finite hyperparameter")
        if alpha <= 0 or beta <= 0 or not 0 < decay <= 1 or not 1 <= max_log_odds <= 50:
            raise ValueError("invalid reliability hyperparameter")
        self.alpha, self.beta = float(alpha), float(beta)
        self.decay, self.max_log_odds = float(decay), float(max_log_odds)
        self.counts: dict[str, tuple[float, float]] = {}
        self.receipts: list[dict] = []
        self._ids: set[str] = set()
        self._pending: tuple[SensorObservation, ...] | None = None

    def reliability(self, origin: str) -> float:
        correct, wrong = self.counts.get(origin, (0., 0.))
        return (self.alpha + correct) / (self.alpha + self.beta + correct + wrong)

    def forecast(self, observations: list[SensorObservation]) -> float:
        if self._pending is not None:
            raise ValueError("previous prediction still awaits feedback")
        if not isinstance(observations, (tuple, list)) or not observations:
            raise ValueError("nonempty observations required")
        seen = set()
        ids = set()
        for item in observations:
            if not isinstance(item, SensorObservation) or not item.origin or not item.evidence_id:
                raise ValueError("invalid source receipt")
            if type(item.value) is not int or item.value not in (0, 1):
                raise ValueError("binary observations required")
            if item.origin in seen or item.evidence_id in ids or item.evidence_id in self._ids:
                raise ValueError("duplicate origin or receipt")
            seen.add(item.origin)
            ids.add(item.evidence_id)
        odds = 0.0
        for item in observations:
            reliability = min(.99, max(.01, self.reliability(item.origin)))
            odds += (2 * item.value - 1) * math.log(reliability / (1 - reliability))
        odds = max(-self.max_log_odds, min(self.max_log_odds, odds))
        self._pending = tuple(observations)
        self._ids.update(ids)
        return 1.0 / (1.0 + math.exp(-odds))

    def learn(self, verified_outcome: int) -> None:
        if self._pending is None:
            raise ValueError("no prediction awaiting feedback")
        if type(verified_outcome) is not int or verified_outcome not in (0, 1):
            raise ValueError("outcome must be a binary integer")
        for item in self._pending:
            correct, wrong = self.counts.get(item.origin, (0., 0.))
            correct *= self.decay
            wrong *= self.decay
            if item.value == verified_outcome:
                correct += 1
            else:
                wrong += 1
            self.counts[item.origin] = (correct, wrong)
        self.receipts.append({"evidence_ids": [item.evidence_id for item in self._pending],
                              "outcome": verified_outcome,
                              "feedback_after_prediction": True})
        self._pending = None

    def skip_feedback(self, *, reason: str) -> None:
        """Close an unresolved forecast without fabricating a binary reward.

        A missing outcome never changes trust counts (including decay).
        Evidence IDs remain consumed and the missing receipt is checkpointed.
        A later genuine outcome cannot be applied retroactively by this API.
        """
        if self._pending is None:
            raise ValueError("no prediction awaiting feedback")
        if (not isinstance(reason, str) or not 1 <= len(reason) <= 120
                or reason != reason.strip()):
            raise ValueError("explicit bounded missing-feedback reason required")
        self.receipts.append({"evidence_ids": [item.evidence_id for item in self._pending],
                              "outcome": None, "feedback_after_prediction": True,
                              "feedback_status": "missing", "reason": reason})
        self._pending = None

    def state(self) -> dict:
        if self._pending is not None:
            raise ValueError("cannot checkpoint with pending unverified outcome")
        return {"schema": "bean.cognitive_gauntlet.sensor_trust.v1",
                "alpha": self.alpha, "beta": self.beta, "decay": self.decay,
                "max_log_odds": self.max_log_odds,
                "counts": {key: list(self.counts[key]) for key in sorted(self.counts)},
                "seen_ids": sorted(self._ids), "receipts": list(self.receipts)}

    @classmethod
    def restore(cls, state: dict):
        if not isinstance(state, dict) or state.get("schema") != "bean.cognitive_gauntlet.sensor_trust.v1":
            raise ValueError("invalid checkpoint schema")
        result = cls(alpha=state["alpha"], beta=state["beta"], decay=state["decay"],
                     max_log_odds=state["max_log_odds"])
        counts = state["counts"]
        if not isinstance(counts, dict):
            raise ValueError("invalid checkpoint counts")
        for k, v in counts.items():
            if (not isinstance(k, str) or not k or not isinstance(v, list) or len(v) != 2
                    or any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in v)):
                raise ValueError("invalid checkpoint counter")
        result.counts = {k: tuple(v) for k, v in counts.items()}
        ids = state["seen_ids"]
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise ValueError("invalid checkpoint evidence ids")
        result._ids = set(ids)
        result.receipts = list(state["receipts"])
        for row in result.receipts:
            if not isinstance(row, dict) or row.get("feedback_after_prediction") is not True:
                raise ValueError("invalid feedback receipt")
            if row.get("feedback_status") == "missing":
                reason = row.get("reason")
                if (row.get("outcome") is not None or not isinstance(reason, str)
                        or not 1 <= len(reason) <= 120 or reason != reason.strip()):
                    raise ValueError("invalid missing-feedback receipt")
            elif (row.get("feedback_status") not in (None, "observed")
                  or type(row.get("outcome")) is not int
                  or row["outcome"] not in (0, 1)):
                raise ValueError("invalid observed-feedback receipt")
        return result
