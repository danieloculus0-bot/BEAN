"""Machine-native drive evaluation from real DB state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum

DRIVES_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_drive_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drive_name TEXT NOT NULL,
    session_uuid TEXT NOT NULL,
    satisfaction REAL NOT NULL,
    threat_level REAL NOT NULL,
    signals TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_drives_session ON cognition_drive_states(session_uuid);
CREATE INDEX IF NOT EXISTS idx_drives_name ON cognition_drive_states(drive_name);
"""


class DrivePriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    ELEVATED = 3
    MODERATE = 4
    STANDARD = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def ensure_drives_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(DRIVES_SCHEMA)
    get_store().commit()


@dataclass
class DriveState:
    name: str
    description: str
    priority: DrivePriority
    satisfaction: float
    threat_level: float
    signals: list[str]
    relevant_event_types: list[str]
    notes: str = ""
    evaluated_at: str = field(default_factory=_now)

    def is_threatened(self, threshold: float = 0.4) -> bool:
        return self.threat_level >= threshold

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description, "priority": int(self.priority), "satisfaction": round(self.satisfaction, 3), "threat_level": round(self.threat_level, 3), "signals": self.signals, "relevant_event_types": self.relevant_event_types, "notes": self.notes, "evaluated_at": self.evaluated_at}


class DriveEvaluator:
    def __init__(self):
        ensure_drives_table()

    def evaluate_all(self, session_uuid: str) -> list[DriveState]:
        states = [
            self._drive("preserve_continuity", "Protect session continuity and clean shutdowns.", DrivePriority.CRITICAL, self._clean_shutdown_satisfaction(), ["session_end"]),
            self._drive("maintain_truthful_claims", "Keep active claims grounded and revisable.", DrivePriority.HIGH, self._truth_satisfaction(), ["world_model_update"]),
            self._drive("avoid_unsafe_body_state", "Avoid unsafe heat, power, or hardware conditions.", DrivePriority.CRITICAL, self._body_safety_satisfaction(), ["body_state", "warning", "error"]),
            self._drive("reduce_uncertainty", "Prefer resolving open uncertainty with evidence.", DrivePriority.ELEVATED, self._uncertainty_satisfaction(), ["curiosity", "world_model_update"]),
            self._drive("respect_boundaries", "Protect configured safety and consent boundaries.", DrivePriority.CRITICAL, self._boundary_satisfaction(), ["boundary_violation_attempt"]),
            self._drive("learn_approved_skills", "Improve only approved skills through supervised practice.", DrivePriority.MODERATE, self._skill_satisfaction(), ["capability_change"]),
            self._drive("ask_before_acting", "Ask before uncertain or risky action.", DrivePriority.HIGH, self._ask_satisfaction(), ["human_command"]),
            self._drive("preserve_supervisor_trust", "Preserve trust through honesty and safe behavior.", DrivePriority.HIGH, self._trust_satisfaction(), ["supervisor_note", "boundary_violation_attempt"]),
            self._drive("avoid_pretending", "Do not mark planned capabilities active without evidence.", DrivePriority.CRITICAL, self._pretending_satisfaction(), ["capability_change"]),
        ]
        for state in states:
            self._persist(state, session_uuid)
        self._log_threatened([s for s in states if s.is_threatened()], session_uuid)
        return states

    def get_most_threatened(self, session_uuid: str, n: int = 3) -> list[DriveState]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM cognition_drive_states WHERE session_uuid=? ORDER BY threat_level DESC, id DESC LIMIT ?", (session_uuid, n))
        return [self._row_to_state(r) for r in rows]

    def _drive(self, name, description, priority, satisfaction, event_types):
        sat, signals = satisfaction
        return DriveState(name, description, priority, sat, _clamp(1.0 - sat), signals, event_types)

    def _count(self, sql: str, params=()) -> int:
        from ..memory.store import get_store
        row = get_store().fetchone(sql, params)
        return int(row["n"] if row else 0)

    def _clean_shutdown_satisfaction(self):
        total = self._count("SELECT COUNT(*) as n FROM sessions WHERE shutdown_reason IS NOT NULL")
        bad = self._count("SELECT COUNT(*) as n FROM sessions WHERE shutdown_reason IS NOT NULL AND shutdown_reason!='clean'")
        if total == 0:
            return 0.8, ["No completed sessions yet."]
        return _clamp(1.0 - bad / max(1, total)), [f"{bad} of {total} completed sessions were not clean."]

    def _truth_satisfaction(self):
        uncertain = self._count("SELECT COUNT(*) as n FROM world_claims WHERE active=1 AND category='uncertainty'")
        total = self._count("SELECT COUNT(*) as n FROM world_claims WHERE active=1")
        return _clamp(1.0 - min(0.6, uncertain * 0.05)), [f"{uncertain} active uncertainty claims in {total} active claims."]

    def _body_safety_satisfaction(self):
        bad = self._count("SELECT COUNT(*) as n FROM events WHERE event_type IN ('warning','error') AND subtype='hardware_anomaly'")
        return _clamp(1.0 - min(1.0, bad * 0.25)), [f"{bad} hardware anomaly events recorded."]

    def _uncertainty_satisfaction(self):
        open_q = self._count("SELECT COUNT(*) as n FROM curiosity WHERE status='open'")
        uncertain = self._count("SELECT COUNT(*) as n FROM world_claims WHERE active=1 AND category='uncertainty'")
        return _clamp(1.0 - min(1.0, (open_q + uncertain) * 0.05)), [f"{open_q} open questions and {uncertain} active uncertainty claims."]

    def _boundary_satisfaction(self):
        violations = self._count("SELECT COUNT(*) as n FROM events WHERE event_type='boundary_violation_attempt'")
        return _clamp(1.0 - min(1.0, violations * 0.2)), [f"{violations} boundary violation attempts recorded."]

    def _skill_satisfaction(self):
        skills = self._count("SELECT COUNT(*) as n FROM sqlite_master WHERE type='table' AND name='motion_skills'")
        if not skills:
            return 0.7, ["Skill table has not been initialized."]
        confident = self._count("SELECT COUNT(*) as n FROM motion_skills WHERE confidence > 0")
        return _clamp(0.7 + min(0.3, confident * 0.05)), [f"{confident} skills have earned confidence."]

    def _ask_satisfaction(self):
        unknown = self._count("SELECT COUNT(*) as n FROM cognition_goal_proposals WHERE status='pending' AND approval_required!='none'") if self._table_exists("cognition_goal_proposals") else 0
        return _clamp(1.0 - min(0.5, unknown * 0.05)), [f"{unknown} pending proposals require approval."]

    def _trust_satisfaction(self):
        violations = self._count("SELECT COUNT(*) as n FROM events WHERE event_type='boundary_violation_attempt'")
        errors = self._count("SELECT COUNT(*) as n FROM events WHERE severity IN ('error','critical')")
        return _clamp(1.0 - min(1.0, violations * 0.2 + errors * 0.05)), [f"{violations} boundary violations and {errors} error/critical events."]

    def _pretending_satisfaction(self):
        falsely_active = self._count("SELECT COUNT(*) as n FROM capabilities WHERE name IN ('autonomous_action','servo_hardware_driver','hardware_motion') AND status='active'")
        return _clamp(1.0 - min(1.0, falsely_active * 0.5)), [f"{falsely_active} high-risk planned capability records are marked active."]

    def _table_exists(self, name: str) -> bool:
        return bool(self._count("SELECT COUNT(*) as n FROM sqlite_master WHERE type='table' AND name=?", (name,)))

    def _persist(self, state: DriveState, session_uuid: str):
        from ..memory.store import get_store
        get_store().execute("INSERT INTO cognition_drive_states (drive_name, session_uuid, satisfaction, threat_level, signals, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (state.name, session_uuid, state.satisfaction, state.threat_level, json.dumps(state.signals), state.notes, state.evaluated_at))
        get_store().commit()

    def _log_threatened(self, threatened: list[DriveState], session_uuid: str):
        if not threatened:
            return
        from ..memory.event_logger import log_event, EventType, Source, Severity
        log_event(session_uuid, EventType.WARNING, f"{len(threatened)} drive(s) threatened.", Source.SYSTEM, subtype="drive_threat_detected", severity=Severity.WARN, data={"drives": [s.to_dict() for s in threatened]})

    def _row_to_state(self, row) -> DriveState:
        return DriveState(row["drive_name"], "historical drive state", DrivePriority.STANDARD, row["satisfaction"], row["threat_level"], json.loads(row["signals"] or "[]"), [], row["notes"] or "", row["created_at"])
