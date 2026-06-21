"""Grounded preference formation from outcome patterns, not fake desire."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

PREFERENCES_SCHEMA = """
CREATE TABLE IF NOT EXISTS cognition_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference_id TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    direction TEXT NOT NULL,
    strength REAL NOT NULL DEFAULT 0.0,
    basis TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '[]',
    supporting_count INTEGER NOT NULL DEFAULT 0,
    contradicting_count INTEGER NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0.0,
    active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_prefs_subject ON cognition_preferences(subject);
CREATE INDEX IF NOT EXISTS idx_prefs_active ON cognition_preferences(active);
"""

MIN_EVIDENCE_FOR_PREFERENCE = 3


class PreferenceDirection(str, Enum):
    TOWARD = "toward"
    AWAY_FROM = "away_from"
    NEUTRAL = "neutral"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_preferences_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(PREFERENCES_SCHEMA)
    get_store().commit()


def _compute_confidence(supporting: int, contradicting: int) -> float:
    total = supporting + contradicting
    if total < MIN_EVIDENCE_FOR_PREFERENCE:
        return 0.0
    consistency = abs(supporting - contradicting) / total if total else 0.0
    sample = min(1.0, math.log(total + 1) / math.log(21))
    return round(max(0.0, min(1.0, sample * (0.5 + 0.5 * consistency))), 3)


def _compute_strength(supporting: int, contradicting: int) -> float:
    total = supporting + contradicting
    return 0.0 if total == 0 else round((supporting - contradicting) / total, 3)


@dataclass
class Preference:
    subject: str
    direction: PreferenceDirection
    strength: float
    basis: str
    evidence: list[str]
    supporting_count: int
    contradicting_count: int
    confidence: float
    notes: str = ""
    active: bool = True
    preference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {"preference_id": self.preference_id, "subject": self.subject, "direction": self.direction.value, "strength": self.strength, "basis": self.basis, "evidence": self.evidence, "supporting_count": self.supporting_count, "contradicting_count": self.contradicting_count, "confidence": self.confidence, "active": self.active, "notes": self.notes, "created_at": self.created_at, "updated_at": self.updated_at}


class PreferenceStore:
    def __init__(self):
        ensure_preferences_table()

    def save(self, pref: Preference):
        from ..memory.store import get_store
        get_store().execute("UPDATE cognition_preferences SET active=0 WHERE subject=? AND active=1", (pref.subject,))
        get_store().execute("""
            INSERT INTO cognition_preferences
                (preference_id, subject, direction, strength, basis, evidence, supporting_count, contradicting_count, confidence, active, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pref.preference_id, pref.subject, pref.direction.value, pref.strength, pref.basis, json.dumps(pref.evidence), pref.supporting_count, pref.contradicting_count, pref.confidence, 1 if pref.active else 0, pref.notes, pref.created_at, pref.updated_at))
        get_store().commit()

    def get(self, subject: str) -> Optional[Preference]:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM cognition_preferences WHERE subject=? AND active=1 ORDER BY id DESC LIMIT 1", (subject,))
        return self._row_to_pref(row) if row else None

    def all_active(self, min_confidence: float = 0.0) -> list[Preference]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM cognition_preferences WHERE active=1 AND confidence>=? ORDER BY confidence DESC", (min_confidence,))
        return [self._row_to_pref(r) for r in rows]

    def snapshot(self) -> list[dict]:
        return [p.to_dict() for p in self.all_active()]

    def _row_to_pref(self, row) -> Preference:
        return Preference(row["subject"], PreferenceDirection(row["direction"]), row["strength"], row["basis"], json.loads(row["evidence"] or "[]"), row["supporting_count"], row["contradicting_count"], row["confidence"], row["notes"] or "", bool(row["active"]), row["preference_id"], row["created_at"], row["updated_at"])


class PreferenceEngine:
    def __init__(self, store: Optional[PreferenceStore] = None):
        self.store = store or PreferenceStore()

    def update_from_history(self, session_uuid: str) -> list[Preference]:
        prefs: list[Preference] = []
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT session_uuid, shutdown_reason FROM sessions WHERE shutdown_reason IS NOT NULL")
        clean = [r["session_uuid"] for r in rows if r["shutdown_reason"] == "clean"]
        unclean = [r["session_uuid"] for r in rows if r["shutdown_reason"] != "clean"]
        conf = _compute_confidence(len(clean), len(unclean))
        if conf > 0:
            strength = _compute_strength(len(clean), len(unclean))
            direction = PreferenceDirection.TOWARD if strength > 0 else PreferenceDirection.AWAY_FROM if strength < 0 else PreferenceDirection.NEUTRAL
            pref = Preference("session.clean_shutdown", direction, strength, "shutdown outcomes correlate with continuity stability", clean[:20] + unclean[:20], len(clean), len(unclean), conf)
            self.store.save(pref)
            prefs.append(pref)
            self._log_preference(pref, session_uuid)
        return prefs

    def record_outcome(self, subject: str, supporting: bool, evidence_ref: str, basis: str, session_uuid: Optional[str] = None) -> Optional[Preference]:
        existing = self.store.get(subject)
        support = (existing.supporting_count if existing else 0) + (1 if supporting else 0)
        contradict = (existing.contradicting_count if existing else 0) + (0 if supporting else 1)
        conf = _compute_confidence(support, contradict)
        if conf <= 0:
            return None
        strength = _compute_strength(support, contradict)
        direction = PreferenceDirection.TOWARD if strength > 0 else PreferenceDirection.AWAY_FROM if strength < 0 else PreferenceDirection.NEUTRAL
        evidence = list(existing.evidence if existing else []) + [evidence_ref]
        pref = Preference(subject, direction, strength, basis, evidence, support, contradict, conf)
        self.store.save(pref)
        if session_uuid:
            self._log_preference(pref, session_uuid)
        return pref

    def _log_preference(self, pref: Preference, session_uuid: str):
        from ..memory.event_logger import log_event, EventType, Source
        log_event(session_uuid, EventType.PREFERENCE_UPDATE, f"Preference updated: {pref.subject}", Source.SYSTEM, subtype="preference_update", data=pref.to_dict())
