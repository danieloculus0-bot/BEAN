"""Reciprocal, uncertainty-aware prototype ranking for opt-in AI matchmaking.

Weights are explicit research hypotheses, NOT statistically calibrated
relationship predictors. No psychological diagnosis or sensitive profile
contents are imported or published.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

FACTOR_WEIGHTS = {
    "mutual_attraction": .19,
    "long_term_goals": .16,
    "communication": .15,
    "conflict_repair": .13,
    "emotional_fit": .12,
    "daily_lifestyle": .10,
    "shared_interests": .06,
    "adaptability": .05,
    "practical_viability": .04,
}
assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 1e-12


def _unit(value, name, allow_none=False):
    if value is None and allow_none:
        return
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(name + " must be a finite number from 0 through 1")


@dataclass(frozen=True)
class FactorObservation:
    """Two local assessments, combined only when BOTH are known.

    a_to_b and b_to_a are directed estimates, not probability forecasts.
    confidence is source-quality evidence, not a psychological measurement.
    """
    a_to_b: float | None
    b_to_a: float | None
    confidence: float = 1.0

    def __post_init__(self):
        _unit(self.a_to_b, "a_to_b", True)
        _unit(self.b_to_a, "b_to_a", True)
        _unit(self.confidence, "confidence")


def compute_fit(observations: dict[str, FactorObservation],
                weights: dict[str, float] | None = None) -> dict:
    """Use geometric reciprocity; unknown directions are NEUTRAL not failures.

    Return an interpretable provisional 0..100 fit index and broad missing-
    evidence bounds; neither represents an actual match probability. Coverage
    and evidence confidence are separate axes. For a required deal breaker,
    a caller must check mutual approval before showing a candidate as viable.
    """
    if not isinstance(observations, dict):
        raise ValueError("factor observations must be a dictionary")
    weights = dict(FACTOR_WEIGHTS if weights is None else weights)
    if set(weights) != set(FACTOR_WEIGHTS):
        raise ValueError("all factor weights required, with no extras")
    for name, weight in weights.items():
        _unit(weight, name)
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ValueError("at least one factor must have positive weight")
    if any(k not in weights or not isinstance(v, FactorObservation)
           for k, v in observations.items()):
        raise ValueError("unknown factor or invalid observation")
    total, coverage, confidence = 0.0, 0.0, 0.0
    seen = {}
    for factor, weight in weights.items():
        weight /= weight_sum
        observation = observations.get(factor)
        if observation is None or observation.a_to_b is None or observation.b_to_a is None:
            total += weight * .5
            seen[factor] = {"status": "unknown", "weight": round(weight, 4),
                            "reciprocal_score": None}
            continue
        # A very low one-way assessment cannot be concealed by enthusiasm
        # from the other side; one direction at zero yields zero for the pair.
        bilateral = math.sqrt(observation.a_to_b * observation.b_to_a)
        total += weight * bilateral
        coverage += weight
        confidence += weight * observation.confidence
        seen[factor] = {"status": "observed", "weight": round(weight, 4),
                        "reciprocal_score": round(bilateral, 4)}
    return {
        "schema": "bean.agent_relay.fit.v1",
        "fit_index": round(total * 100, 2) if coverage > 0 else None,
        "factor_coverage_pct": round(coverage * 100, 2),
        "evidence_confidence_pct": round(confidence * 100, 2),
        "unknown_weight_pct": round((1 - coverage) * 100, 2),
        "provisional_lower_bound": round((total - .5 * (1 - coverage)) * 100, 2),
        "provisional_upper_bound": round((total + .5 * (1 - coverage)) * 100, 2),
        "factors": seen,
        "calibrated_probability": None,
        "validated_relationship_prediction": False,
    }


class EvidenceLedger:
    """Local-only updateable assessments with idempotent round receipts.

    Same source repeated must not manufacture confidence. Independent new
    rounds may revise prior assessments; both histories remain observable.
    """

    def __init__(self):
        self._rounds: dict[str, dict] = {}
        self._history: list[dict] = []

    def observe(self, candidate_id: str, factor: str, observation: FactorObservation,
                *, receipt_id: str):
        if (not isinstance(candidate_id, str) or not candidate_id.isascii()
                or not 1 <= len(candidate_id) <= 64
                or factor not in FACTOR_WEIGHTS
                or not isinstance(observation, FactorObservation)
                or not isinstance(receipt_id, str) or not receipt_id.isascii()
                or not 4 <= len(receipt_id) <= 100):
            raise ValueError("invalid private factor receipt")
        key = (candidate_id, receipt_id)
        proposed = (factor, observation)
        if key in self._rounds:
            if self._rounds[key] != proposed:
                raise ValueError("conflicting evidence receipt")
            return False
        self._rounds[key] = proposed
        self._history.append({"candidate_id": candidate_id, "factor": factor,
                              "observation": observation, "receipt_id": receipt_id})
        return True

    def latest(self, candidate_id: str) -> dict[str, FactorObservation]:
        result = {}
        for event in self._history:
            if event["candidate_id"] == candidate_id:
                result[event["factor"]] = event["observation"]
        return result

    def score(self, candidate_id: str, weights=None) -> dict:
        return compute_fit(self.latest(candidate_id), weights=weights)

    def conversation_count(self, candidate_id: str) -> int:
        return len({row["receipt_id"] for row in self._history
                    if row["candidate_id"] == candidate_id})
