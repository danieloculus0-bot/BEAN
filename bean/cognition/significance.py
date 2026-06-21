"""
bean/cognition/significance.py

Scores logged events for significance without pretending that attention is emotion.
A score says "this deserves processing," not "BEAN feels something."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..memory.event_logger import EventType, Severity

DEFAULT_EVENT_TYPE_WEIGHTS = {
    EventType.SAFETY_TRIGGER.value: 1.0,
    EventType.BOUNDARY_VIOLATION_ATTEMPT.value: 1.0,
    EventType.OVERRIDE.value: 0.9,
    EventType.ERROR.value: 0.85,
    EventType.WARNING.value: 0.6,
    EventType.SUPERVISOR_NOTE.value: 0.8,
    EventType.HUMAN_COMMAND.value: 0.75,
    EventType.HUMAN_INPUT.value: 0.65,
    EventType.FACT_LEARNED.value: 0.7,
    EventType.CAPABILITY_CHANGE.value: 0.75,
    EventType.CODE_CHANGE.value: 0.8,
    EventType.WORLD_MODEL_UPDATE.value: 0.6,
    EventType.SELF_MODEL_UPDATE.value: 0.6,
    EventType.REFLECTION.value: 0.5,
    EventType.CURIOSITY.value: 0.55,
    EventType.MEMORY_CONSOLIDATION.value: 0.5,
    EventType.BODY_STATE.value: 0.2,
    EventType.OBSERVATION.value: 0.35,
    EventType.SENSOR_READING.value: 0.3,
    EventType.BOOT.value: 0.3,
    EventType.SHUTDOWN.value: 0.4,
    EventType.SESSION_START.value: 0.25,
    EventType.SESSION_END.value: 0.35,
    EventType.LLM_RESPONSE.value: 0.5,
    EventType.PREFERENCE_UPDATE.value: 0.6,
    EventType.BOUNDARY_DECISION.value: 0.7,
}

DEFAULT_SEVERITY_MODIFIERS = {
    Severity.DEBUG.value: -0.1,
    Severity.INFO.value: 0.0,
    Severity.WARN.value: 0.15,
    Severity.ERROR.value: 0.25,
    Severity.CRITICAL.value: 0.35,
}

DEFAULT_SUBTYPE_MODIFIERS = {
    "hardware_anomaly": 0.25,
    "tick_handler_error": 0.25,
    "inbox_handler_error": 0.2,
    "surprise:claim_contradicted": 0.2,
    "model_update:manual": 0.1,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class SignificanceScore:
    event_id: Optional[int]
    event_type: str
    subtype: Optional[str]
    severity: str
    score: float
    reasons: list[str] = field(default_factory=list)

    def is_notable(self, threshold: float = 0.5) -> bool:
        return self.score >= threshold

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "subtype": self.subtype,
            "severity": self.severity,
            "score": round(self.score, 3),
            "reasons": list(self.reasons),
        }


class SignificanceScorer:
    def __init__(self, type_scores=None, severity_modifiers=None, subtype_modifiers=None):
        self.type_scores = dict(type_scores or DEFAULT_EVENT_TYPE_WEIGHTS)
        self.severity_modifiers = dict(severity_modifiers or DEFAULT_SEVERITY_MODIFIERS)
        self.subtype_modifiers = dict(subtype_modifiers or DEFAULT_SUBTYPE_MODIFIERS)

    def score_event(self, event: dict) -> SignificanceScore:
        etype = str(event.get("event_type") or "unknown")
        severity = str(event.get("severity") or "info")
        subtype = event.get("subtype")
        base = self.type_scores.get(etype, 0.2)
        sev_mod = self.severity_modifiers.get(severity, 0.0)
        sub_mod = self.subtype_modifiers.get(str(subtype), 0.0) if subtype else 0.0
        score = _clamp(base + sev_mod + sub_mod)
        reasons = [f"base[{etype}]={base:.2f}"]
        if sev_mod:
            reasons.append(f"severity[{severity}]={sev_mod:+.2f}")
        if subtype and sub_mod:
            reasons.append(f"subtype[{subtype}]={sub_mod:+.2f}")
        return SignificanceScore(event.get("id"), etype, subtype, severity, score, reasons)

    def score_events(self, events: list[dict]) -> list[SignificanceScore]:
        return [self.score_event(e) for e in events]

    def top_events(self, events: list[dict], n: int = 10, threshold: float = 0.0) -> list[SignificanceScore]:
        scored = [s for s in self.score_events(events) if s.score >= threshold]
        return sorted(scored, key=lambda s: s.score, reverse=True)[:n]

    def update_type_score(self, event_type: str, score: float, session_uuid: Optional[str] = None, reason: str = "manual"):
        self.type_scores[event_type] = _clamp(score)
        if session_uuid:
            from ..memory.event_logger import log_event, Source
            log_event(session_uuid, EventType.CONFIG_CHANGE, f"Significance score updated for {event_type}.", Source.HUMAN, subtype="significance_score_update", data={"event_type": event_type, "score": self.type_scores[event_type], "reason": reason})

    def weights_snapshot(self) -> dict:
        return {"event_type_weights": self.type_scores, "severity_modifiers": self.severity_modifiers, "subtype_modifiers": self.subtype_modifiers}


def score_recent_events(session_uuid: str, limit: int = 50, threshold: float = 0.5) -> list[dict]:
    from ..memory.event_logger import get_recent_events
    scorer = SignificanceScorer()
    return [s.to_dict() for s in scorer.top_events(get_recent_events(session_uuid, limit), n=limit, threshold=threshold)]
