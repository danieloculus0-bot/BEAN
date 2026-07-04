"""Rule-based trigger detection for Brain 0.9 wisdom."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TriggerMatch:
    trigger_type: str
    weight: float
    evidence: list[str]

    def to_dict(self) -> dict:
        return {"trigger_type": self.trigger_type, "weight": self.weight, "evidence": self.evidence}


TRIGGER_RULES = {
    "future_plan_disruption": ["trip", "plan", "future", "declined", "cancelled", "canceled"],
    "social_no_marker": ["declined", "no", "ignored"],
    "expectation_violation": ["expected", "supposed to", "instead", "changed"],
    "relationship_significance_marker": ["partner", "relationship", "trust", "belonging", "support"],
    "contradiction_trigger": ["contradiction", "does not match", "conflict", "inconsistent"],
    "uncertainty_trigger": ["maybe", "uncertain", "unknown", "not sure", "confused"],
    "trust_concern_trigger": ["trust issue", "trust concern"],
    "agency_limit_trigger": ["no choice", "limited choice", "no control"],
    "repair_opportunity_trigger": ["apology", "repair", "clarify", "reassure", "acknowledge"],
}


def match_triggers(event_summary: str, event_data: dict | None = None) -> list[TriggerMatch]:
    text = f"{event_summary or ''} {event_data or ''}".lower()
    matches: list[TriggerMatch] = []
    for trigger_type, words in TRIGGER_RULES.items():
        hits = [word for word in words if word in text]
        if hits:
            weight = min(1.0, 0.35 + 0.15 * len(hits))
            matches.append(TriggerMatch(trigger_type, weight, hits))
    matches.sort(key=lambda m: m.weight, reverse=True)
    return matches


def root_trigger(matches: list[TriggerMatch]) -> str:
    return matches[0].trigger_type if matches else "unclassified_event"
