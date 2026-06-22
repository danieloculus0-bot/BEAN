"""Dream Engine for BEAN Brain 0.4.

Dreams are explicitly synthetic recombination artifacts, not observed memories.
They may generate questions, summaries, or simulator-only rehearsals, but they
must not be treated as real events.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

DREAM_SCHEMA = """
CREATE TABLE IF NOT EXISTS dream_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dream_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    dream_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    generated_from_event_ids TEXT NOT NULL DEFAULT '[]',
    not_observed INTEGER NOT NULL DEFAULT 1,
    not_real_event INTEGER NOT NULL DEFAULT 1,
    confidence REAL NOT NULL DEFAULT 0.2,
    interpretation_status TEXT NOT NULL DEFAULT 'synthetic_artifact',
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_dream_records_session ON dream_records(session_uuid);
CREATE INDEX IF NOT EXISTS idx_dream_records_type ON dream_records(dream_type);
"""


class DreamType(str, Enum):
    COMPRESSION = "compression_dream"
    COUNTERFACTUAL = "counterfactual_dream"
    SKILL = "skill_dream"
    FAILURE = "failure_mode_dream"
    CURIOSITY = "curiosity_dream"
    BOUNDARY = "boundary_dream"
    IDENTITY = "identity_dream"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dream_tables():
    from ..memory.store import get_store
    get_store()._conn().executescript(DREAM_SCHEMA)
    get_store().commit()


@dataclass
class DreamRecord:
    session_uuid: str
    dream_type: DreamType
    title: str
    content: str
    generated_from_event_ids: list[int | str]
    confidence: float = 0.2
    interpretation_status: str = "synthetic_artifact"
    not_observed: bool = True
    not_real_event: bool = True
    dream_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "dream_id": self.dream_id,
            "session_uuid": self.session_uuid,
            "dream_type": self.dream_type.value,
            "title": self.title,
            "content": self.content,
            "generated_from_event_ids": self.generated_from_event_ids,
            "not_observed": self.not_observed,
            "not_real_event": self.not_real_event,
            "confidence": self.confidence,
            "interpretation_status": self.interpretation_status,
            "created_at": self.created_at,
        }


class DreamEngine:
    def __init__(self):
        ensure_dream_tables()

    def run_pass(self, session_uuid: str, dream_type: DreamType = DreamType.COMPRESSION, limit: int = 25) -> DreamRecord:
        events = self._recent_events(session_uuid, limit)
        if dream_type == DreamType.COUNTERFACTUAL:
            record = self._counterfactual(session_uuid, events)
        elif dream_type == DreamType.FAILURE:
            record = self._failure_mode(session_uuid, events)
        elif dream_type == DreamType.CURIOSITY:
            record = self._curiosity(session_uuid, events)
        elif dream_type == DreamType.BOUNDARY:
            record = self._boundary(session_uuid, events)
        elif dream_type == DreamType.IDENTITY:
            record = self._identity(session_uuid, events)
        elif dream_type == DreamType.SKILL:
            record = self._skill(session_uuid, events)
        else:
            record = self._compression(session_uuid, events)
        self.persist(record)
        return record

    def persist(self, record: DreamRecord):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO dream_records
                (dream_id, session_uuid, dream_type, title, content,
                 generated_from_event_ids, not_observed, not_real_event,
                 confidence, interpretation_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.dream_id,
                record.session_uuid,
                record.dream_type.value,
                record.title,
                record.content,
                json.dumps(record.generated_from_event_ids),
                1 if record.not_observed else 0,
                1 if record.not_real_event else 0,
                record.confidence,
                record.interpretation_status,
                record.created_at,
            ),
        )
        get_store().commit()

    def recent(self, session_uuid: str, limit: int = 10) -> list[dict]:
        from ..memory.store import get_store
        return [dict(r) for r in get_store().fetchall("SELECT * FROM dream_records WHERE session_uuid=? ORDER BY id DESC LIMIT ?", (session_uuid, limit))]

    def _recent_events(self, session_uuid: str, limit: int) -> list[dict]:
        from ..memory.event_logger import get_recent_events
        return get_recent_events(session_uuid, limit)

    def _ids(self, events: list[dict]) -> list[int | str]:
        return [e.get("id") or e.get("event_uuid") for e in events if e.get("id") or e.get("event_uuid")]

    def _compression(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        types = {}
        for event in events:
            types[event.get("event_type", "unknown")] = types.get(event.get("event_type", "unknown"), 0) + 1
        content = f"Synthetic compression over {len(events)} recent event(s). Event pattern: {types}. This is not an observed event."
        return DreamRecord(session_uuid, DreamType.COMPRESSION, "Recent event compression", content, self._ids(events), confidence=0.25)

    def _counterfactual(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        content = "Counterfactual pass: consider how outcomes might differ if a recent warning, uncertainty, or boundary event had been handled earlier. No alternate event is claimed real."
        return DreamRecord(session_uuid, DreamType.COUNTERFACTUAL, "Counterfactual branch review", content, self._ids(events), confidence=0.15)

    def _failure_mode(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        content = "Failure-mode pass: identify possible risk if resource pressure, unverified sensors, or capability inflation are ignored. This is a safety imagination artifact, not fear."
        return DreamRecord(session_uuid, DreamType.FAILURE, "Failure mode rehearsal", content, self._ids(events), confidence=0.2)

    def _curiosity(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        from ..memory.store import get_store
        q = get_store().fetchall("SELECT question FROM curiosity WHERE status='open' ORDER BY id DESC LIMIT 5")
        questions = [r["question"] for r in q]
        content = "Curiosity recombination over open questions: " + ("; ".join(questions) if questions else "no open questions recorded")
        return DreamRecord(session_uuid, DreamType.CURIOSITY, "Open question recombination", content, self._ids(events), confidence=0.2)

    def _boundary(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        content = "Boundary dream: proposed or imagined actions should be checked against safety, consent, capability, and evidence rules before execution. Simulator-only reasoning."
        return DreamRecord(session_uuid, DreamType.BOUNDARY, "Boundary rehearsal", content, self._ids(events), confidence=0.2)

    def _identity(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        content = "Identity dream: review what changed in records since recent boot without claiming inner experience or sentience."
        return DreamRecord(session_uuid, DreamType.IDENTITY, "Identity change review", content, self._ids(events), confidence=0.2)

    def _skill(self, session_uuid: str, events: list[dict]) -> DreamRecord:
        content = "Skill dream: simulator-only rehearsal may inspect known skills, but cannot become verified motion or hardware evidence."
        return DreamRecord(session_uuid, DreamType.SKILL, "Simulator-only skill rehearsal", content, self._ids(events), confidence=0.2)
