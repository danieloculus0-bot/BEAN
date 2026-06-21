"""Detect mismatches between fresh events and active self/world claims."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

SURPRISE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_surprises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    surprise_id TEXT NOT NULL UNIQUE,
    surprise_type TEXT NOT NULL,
    severity REAL NOT NULL,
    description TEXT NOT NULL,
    trigger_event_id INTEGER,
    trigger_event_type TEXT,
    trigger_event_summary TEXT,
    contradicted_claim_key TEXT,
    contradicted_claim_content TEXT,
    indicated_actions TEXT,
    generated_question TEXT,
    resolved INTEGER NOT NULL DEFAULT 0,
    session_uuid TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_surprises_session ON cognition_surprises(session_uuid);
CREATE INDEX IF NOT EXISTS idx_surprises_resolved ON cognition_surprises(resolved);
"""


class SurpriseType(str, Enum):
    CLAIM_CONTRADICTED = "claim_contradicted"
    NOVEL_EVENT_TYPE = "novel_event_type"
    UNEXPECTED_HARDWARE_STATE = "unexpected_hardware_state"


class SurpriseAction(str, Enum):
    FLAG_FOR_MODEL_UPDATE = "flag_for_model_update"
    ASK_CURIOSITY_QUESTION = "ask_curiosity_question"
    REQUIRE_SUPERVISOR_REVIEW = "require_supervisor_review"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_surprises_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(SURPRISE_SCHEMA)
    get_store().commit()


@dataclass
class SurpriseRecord:
    surprise_type: SurpriseType
    severity: float
    description: str
    trigger_event_id: Optional[int] = None
    trigger_event_type: Optional[str] = None
    trigger_event_summary: Optional[str] = None
    contradicted_claim_key: Optional[str] = None
    contradicted_claim_content: Optional[str] = None
    indicated_actions: list[SurpriseAction] = field(default_factory=list)
    generated_question: Optional[str] = None
    surprise_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {"surprise_id": self.surprise_id, "surprise_type": self.surprise_type.value, "severity": round(self.severity, 3), "description": self.description, "trigger_event_id": self.trigger_event_id, "trigger_event_type": self.trigger_event_type, "trigger_event_summary": self.trigger_event_summary, "contradicted_claim_key": self.contradicted_claim_key, "contradicted_claim_content": self.contradicted_claim_content, "indicated_actions": [a.value for a in self.indicated_actions], "generated_question": self.generated_question, "created_at": self.created_at}


class SurpriseDetector:
    def __init__(self, model_store=None):
        ensure_surprises_table()
        self._model_store = model_store

    def _store(self):
        if self._model_store is None:
            from ..world.model_store import ModelStore
            self._model_store = ModelStore()
        return self._model_store

    def check_event(self, event: dict, session_uuid: str) -> list[SurpriseRecord]:
        records: list[SurpriseRecord] = []
        records.extend(self._check_sensor_uncertainty(event, "vision", ["camera", "vision", "image"], "environment.uncertainty.no_vision"))
        records.extend(self._check_sensor_uncertainty(event, "audio", ["audio", "microphone", "sound"], "environment.uncertainty.no_audio"))
        records.extend(self._check_novel_event_type(event))
        for record in records:
            self._persist(record, session_uuid)
            self._log(record, session_uuid)
            self._generate_question(record, session_uuid)
        return records

    def check_events_batch(self, events: list[dict], session_uuid: str) -> list[SurpriseRecord]:
        out: list[SurpriseRecord] = []
        for event in events:
            out.extend(self.check_event(event, session_uuid))
        return out

    def _check_sensor_uncertainty(self, event: dict, label: str, markers: list[str], claim_key: str) -> list[SurpriseRecord]:
        etype = str(event.get("event_type") or "")
        subtype = str(event.get("subtype") or "")
        text = f"{etype} {subtype} {event.get('summary') or ''}".lower()
        if etype != "sensor_reading" or not any(m in text for m in markers):
            return []
        claim = self._store().get_active(claim_key)
        if not claim:
            return []
        return [SurpriseRecord(SurpriseType.CLAIM_CONTRADICTED, 0.8, f"A {label} event arrived while an active uncertainty claim says no {label} data exists.", event.get("id"), etype, event.get("summary"), claim.key, claim.content, [SurpriseAction.FLAG_FOR_MODEL_UPDATE, SurpriseAction.ASK_CURIOSITY_QUESTION])]

    def _check_novel_event_type(self, event: dict) -> list[SurpriseRecord]:
        from ..memory.store import get_store
        etype = str(event.get("event_type") or "unknown")
        row = get_store().fetchone("SELECT COUNT(*) as n FROM events WHERE event_type=?", (etype,))
        if row and row["n"] == 0 and etype not in {"body_state", "session_start", "session_end"}:
            return [SurpriseRecord(SurpriseType.NOVEL_EVENT_TYPE, 0.4, f"Event type has not appeared in memory before: {etype}.", event.get("id"), etype, event.get("summary"), indicated_actions=[SurpriseAction.FLAG_FOR_MODEL_UPDATE])]
        return []

    def _persist(self, record: SurpriseRecord, session_uuid: str):
        from ..memory.store import get_store
        get_store().execute("""
            INSERT OR IGNORE INTO cognition_surprises
                (surprise_id, surprise_type, severity, description, trigger_event_id, trigger_event_type, trigger_event_summary, contradicted_claim_key, contradicted_claim_content, indicated_actions, generated_question, resolved, session_uuid, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (record.surprise_id, record.surprise_type.value, record.severity, record.description, record.trigger_event_id, record.trigger_event_type, record.trigger_event_summary, record.contradicted_claim_key, record.contradicted_claim_content, json.dumps([a.value for a in record.indicated_actions]), record.generated_question, session_uuid, record.created_at))
        get_store().commit()

    def _log(self, record: SurpriseRecord, session_uuid: str):
        from ..memory.event_logger import log_event, EventType, Source, Severity
        log_event(session_uuid, EventType.WORLD_MODEL_UPDATE, f"Surprise detected: {record.description}", Source.SYSTEM, subtype=f"surprise:{record.surprise_type.value}", severity=Severity.WARN if record.severity >= 0.6 else Severity.INFO, data=record.to_dict())

    def _generate_question(self, record: SurpriseRecord, session_uuid: str):
        if SurpriseAction.ASK_CURIOSITY_QUESTION not in record.indicated_actions:
            return
        question = record.generated_question or f"What changed that made this claim questionable: {record.contradicted_claim_key}?"
        from ..memory.store import get_store
        get_store().execute("INSERT INTO curiosity (question, context, status, created_at) VALUES (?, ?, 'open', ?)", (question, record.description, _now()))
        get_store().commit()

    def get_unresolved(self, session_uuid: Optional[str] = None) -> list[dict]:
        from ..memory.store import get_store
        if session_uuid:
            rows = get_store().fetchall("SELECT * FROM cognition_surprises WHERE resolved=0 AND session_uuid=? ORDER BY id DESC", (session_uuid,))
        else:
            rows = get_store().fetchall("SELECT * FROM cognition_surprises WHERE resolved=0 ORDER BY id DESC")
        return [dict(r) for r in rows]

    def resolve(self, surprise_id: str):
        from ..memory.store import get_store
        get_store().execute("UPDATE cognition_surprises SET resolved=1 WHERE surprise_id=?", (surprise_id,))
        get_store().commit()
