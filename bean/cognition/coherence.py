"""Coherence windows reweight and sometimes collapse possibility states."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .entropy import EntropySource
from .possibility import COLLAPSE_THRESHOLD, PossibilityState
from .state_collapse import StateCollapseManager

COHERENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_coherence_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    trigger TEXT NOT NULL,
    states_reviewed INTEGER NOT NULL,
    reweight_events INTEGER NOT NULL,
    collapse_events INTEGER NOT NULL,
    noise_injections INTEGER NOT NULL,
    report TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_coherence_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(COHERENCE_SCHEMA)
    get_store().commit()


@dataclass
class ReweightEvent:
    state_name: str
    observation: str
    observation_ref: Optional[str]
    weights_before: dict[str, float]
    weights_after: dict[str, float]
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class CollapseEvent:
    state_name: str
    collapsed_to: str
    probability: float
    observation: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class CoherenceReport:
    window_id: str
    session_uuid: str
    trigger: str
    states_reviewed: int
    reweight_events: list[ReweightEvent]
    collapse_events: list[CollapseEvent]
    noise_injections: int
    notes: list[str]
    created_at: str

    def to_dict(self) -> dict:
        return {"window_id": self.window_id, "session_uuid": self.session_uuid, "trigger": self.trigger, "states_reviewed": self.states_reviewed, "reweight_events": [r.to_dict() for r in self.reweight_events], "collapse_events": [c.to_dict() for c in self.collapse_events], "noise_injections": self.noise_injections, "notes": self.notes, "created_at": self.created_at}


class CoherenceEngine:
    def __init__(self, state_manager: Optional[StateCollapseManager] = None, entropy: Optional[EntropySource] = None):
        ensure_coherence_table()
        self.state_manager = state_manager or StateCollapseManager()
        self.entropy = entropy or EntropySource()

    def run(self, session_uuid: str, trigger: str = "idle", recent_events: Optional[list[dict]] = None) -> CoherenceReport:
        recent_events = recent_events if recent_events is not None else self._recent_events(session_uuid)
        reweights: list[ReweightEvent] = []
        collapses: list[CollapseEvent] = []
        noise_count = 0
        for state in self.state_manager.all_uncollapsed():
            before = state.normalized_weights()
            changed = self._apply_evidence(state, recent_events)
            if not changed:
                changed = self._inject_noise(state)
                noise_count += 1 if changed else 0
            if changed:
                self.state_manager.update(state)
                after = state.normalized_weights()
                rw = ReweightEvent(state.name, "coherence evidence/noise pass", trigger, before, after)
                reweights.append(rw)
                self.state_manager.record_reweight(state.name, rw.observation, rw.observation_ref, before, after, session_uuid)
            dominant = state.dominant_option()
            prob = state.dominant_probability()
            if dominant and prob >= COLLAPSE_THRESHOLD:
                obs = f"Dominant option exceeded collapse threshold: {dominant.key} at {prob:.3f}."
                if self.state_manager.collapse(state.name, dominant.key, obs, trigger, session_uuid):
                    collapses.append(CollapseEvent(state.name, dominant.key, prob, obs))
        report = CoherenceReport(str(uuid.uuid4()), session_uuid, trigger, len(self.state_manager.all_active()), reweights, collapses, noise_count, [], _now())
        self._persist(report)
        self._log(report)
        return report

    def _apply_evidence(self, state: PossibilityState, events: list[dict]) -> bool:
        changed = False
        hay = "\n".join(f"{e.get('event_type')} {e.get('subtype')} {e.get('summary')}" for e in events).lower()
        def boost(key, amount):
            nonlocal changed
            opt = state.option(key)
            if opt:
                opt.weight += amount
                changed = True
        if state.name == "vision_state" and any(x in hay for x in ("camera", "vision", "image")):
            boost("camera_active_logging", 1.0)
        if state.name == "audio_state" and any(x in hay for x in ("audio", "microphone", "sound")):
            boost("audio_active_logging", 1.0)
        if state.name == "hardware_motion_state" and any(x in hay for x in ("hardware_motion", "servo", "motor")):
            boost("hardware_motion_verified", 1.0)
        if state.name == "supervisor_presence_state" and any(x in hay for x in ("supervisor", "human_command", "supervisor_note")):
            boost("present_monitoring", 0.5)
        return changed

    def _inject_noise(self, state: PossibilityState) -> bool:
        if state.collapsed:
            return False
        reading = self.entropy.sample_gaussian(mean=0.0, std=0.01, usage_hint=f"coherence_noise:{state.name}")
        opt = state.dominant_option()
        if not opt:
            return False
        opt.weight = max(0.0001, opt.weight + reading.value)
        return True

    def _recent_events(self, session_uuid: str, limit: int = 50) -> list[dict]:
        from ..memory.event_logger import get_recent_events
        return get_recent_events(session_uuid, limit)

    def _persist(self, report: CoherenceReport):
        from ..memory.store import get_store
        get_store().execute("INSERT INTO cognition_coherence_windows (window_id, session_uuid, trigger, states_reviewed, reweight_events, collapse_events, noise_injections, report, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (report.window_id, report.session_uuid, report.trigger, report.states_reviewed, len(report.reweight_events), len(report.collapse_events), report.noise_injections, json.dumps(report.to_dict()), report.created_at))
        get_store().commit()

    def _log(self, report: CoherenceReport):
        from ..memory.event_logger import log_event, EventType, Source
        log_event(report.session_uuid, EventType.MEMORY_CONSOLIDATION, f"Coherence window complete: {report.states_reviewed} states reviewed.", Source.SYSTEM, subtype=f"coherence_window:{report.trigger}", data=report.to_dict())
