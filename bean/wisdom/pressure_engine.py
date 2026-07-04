"""Pressure-state calculation for Brain 0.9 wisdom."""

from __future__ import annotations

from .schema import PRESSURE_DIMENSIONS

PRESSURE_MAP = {
    "future_plan_disruption": {"future_plan_threat": 0.40, "uncertainty_load": 0.25},
    "social_no_marker": {"rejection_pressure": 0.25, "belonging_threat": 0.15},
    "expectation_violation": {"uncertainty_load": 0.25, "contradiction_load": 0.20},
    "relationship_significance_marker": {"trust_damage": 0.15, "belonging_threat": 0.20},
    "contradiction_trigger": {"contradiction_load": 0.45, "uncertainty_load": 0.25},
    "uncertainty_trigger": {"uncertainty_load": 0.35},
    "trust_concern_trigger": {"trust_damage": 0.35, "uncertainty_load": 0.15},
    "agency_limit_trigger": {"agency_threat": 0.35, "uncertainty_load": 0.10},
    "repair_opportunity_trigger": {"uncertainty_load": -0.10, "trust_damage": -0.10},
}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_pressure_delta(trigger_matches: list, associations: list | None = None) -> dict:
    delta = {name: 0.0 for name in PRESSURE_DIMENSIONS}
    for match in trigger_matches:
        trigger_type = match.trigger_type if hasattr(match, "trigger_type") else match.get("trigger_type")
        weight = match.weight if hasattr(match, "weight") else match.get("weight", 0.5)
        for dim, amount in PRESSURE_MAP.get(trigger_type, {}).items():
            delta[dim] = _bounded(delta.get(dim, 0.0) + amount * float(weight))
    for assoc in associations or []:
        if assoc.get("association_type") == "recurs_with":
            delta["uncertainty_load"] = _bounded(delta["uncertainty_load"] + 0.05)
    return delta


def reduced_pressure(before: dict, after: dict) -> bool:
    return sum(after.get(k, 0.0) for k in PRESSURE_DIMENSIONS) < sum(before.get(k, 0.0) for k in PRESSURE_DIMENSIONS)
