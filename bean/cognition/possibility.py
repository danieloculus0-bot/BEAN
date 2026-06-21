"""Possibility states hold multiple interpretations before forced certainty."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

COLLAPSE_THRESHOLD = 0.85

POSSIBILITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_possibility_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    options TEXT NOT NULL,
    collapsed INTEGER NOT NULL DEFAULT 0,
    collapsed_to TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE TABLE IF NOT EXISTS cognition_state_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    state_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    observation TEXT NOT NULL,
    observation_ref TEXT,
    weights_before TEXT NOT NULL,
    weights_after TEXT NOT NULL,
    collapsed_to TEXT,
    session_uuid TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_state_events_name ON cognition_state_events(state_name);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_possibility_tables():
    from ..memory.store import get_store
    get_store()._conn().executescript(POSSIBILITY_SCHEMA)
    get_store().commit()


@dataclass
class StateOption:
    key: str
    description: str
    weight: float
    evidence: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {"key": self.key, "description": self.description, "weight": round(float(self.weight), 6), "evidence": self.evidence, "notes": self.notes}

    @classmethod
    def from_dict(cls, d: dict) -> "StateOption":
        return cls(d["key"], d["description"], float(d.get("weight", 0.0)), d.get("evidence", []), d.get("notes", ""))


@dataclass
class PossibilityState:
    state_id: str
    name: str
    description: str
    options: list[StateOption]
    collapsed: bool = False
    collapsed_to: Optional[str] = None
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def normalized_weights(self) -> dict[str, float]:
        total = sum(max(0.0, o.weight) for o in self.options)
        if total <= 0:
            return {o.key: 1.0 / len(self.options) for o in self.options} if self.options else {}
        return {o.key: max(0.0, o.weight) / total for o in self.options}

    def dominant_option(self) -> Optional[StateOption]:
        return max(self.options, key=lambda o: o.weight, default=None)

    def dominant_probability(self) -> float:
        dominant = self.dominant_option()
        return self.normalized_weights().get(dominant.key, 0.0) if dominant else 0.0

    def is_collapsed(self) -> bool:
        return self.collapsed or self.dominant_probability() >= COLLAPSE_THRESHOLD

    def option(self, key: str) -> Optional[StateOption]:
        return next((o for o in self.options if o.key == key), None)

    def to_dict(self) -> dict:
        return {"state_id": self.state_id, "name": self.name, "description": self.description, "options": [o.to_dict() for o in self.options], "normalized_weights": self.normalized_weights(), "collapsed": self.collapsed, "collapsed_to": self.collapsed_to, "active": self.active, "created_at": self.created_at, "updated_at": self.updated_at}


def build_initial_possibility_states() -> list[PossibilityState]:
    return [
        PossibilityState(str(uuid.uuid4()), "vision_state", "Whether visual sensing is producing logged data.", [StateOption("no_camera_data", "No camera data has been logged.", 0.8), StateOption("camera_active_logging", "Camera events are being logged.", 0.0), StateOption("camera_available_unverified", "Camera may exist but has not produced logged evidence.", 0.2)]),
        PossibilityState(str(uuid.uuid4()), "audio_state", "Whether audio sensing is producing logged data.", [StateOption("no_audio_data", "No audio data has been logged.", 0.8), StateOption("audio_active_logging", "Audio events are being logged.", 0.0), StateOption("audio_available_unverified", "Audio may exist but has not produced logged evidence.", 0.2)]),
        PossibilityState(str(uuid.uuid4()), "hardware_motion_state", "Whether real hardware motion is verified.", [StateOption("simulator_only", "Motion is simulated only.", 0.9), StateOption("hardware_motion_verified", "Real hardware motion has been verified.", 0.0), StateOption("hardware_present_unverified", "Hardware may be present but is not verified.", 0.1)]),
        PossibilityState(str(uuid.uuid4()), "supervisor_presence_state", "Whether a supervisor is present or monitoring.", [StateOption("presence_unknown", "Supervisor presence is unknown.", 0.6), StateOption("present_monitoring", "Supervisor is present or monitoring.", 0.3), StateOption("not_present", "Supervisor is not present.", 0.1)]),
    ]
