"""Versioned, supervisor-adjustable significance weights stored in SQLite."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .significance import DEFAULT_EVENT_TYPE_WEIGHTS, DEFAULT_SEVERITY_MODIFIERS, DEFAULT_SUBTYPE_MODIFIERS

WEIGHTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS significance_weight_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL UNIQUE,
    version INTEGER NOT NULL,
    label TEXT NOT NULL DEFAULT 'default',
    event_type_weights TEXT NOT NULL,
    severity_modifiers TEXT NOT NULL,
    subtype_modifiers TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    changed_by TEXT NOT NULL DEFAULT 'system',
    change_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_sig_weights_active ON significance_weight_profiles(active);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def ensure_weights_table():
    from ..memory.store import get_store
    store = get_store()
    store._conn().executescript(WEIGHTS_SCHEMA)
    store.commit()


@dataclass
class SignificanceWeights:
    profile_id: str
    version: int
    label: str
    event_type_weights: dict[str, float]
    severity_modifiers: dict[str, float]
    subtype_modifiers: dict[str, float]
    changed_by: str = "system"
    change_reason: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def get_event_score(self, event_type: str) -> float:
        return float(self.event_type_weights.get(event_type, 0.2))

    def get_severity_modifier(self, severity: str) -> float:
        return float(self.severity_modifiers.get(severity, 0.0))

    def get_subtype_modifier(self, subtype: str) -> float:
        return float(self.subtype_modifiers.get(subtype, 0.0))

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class SignificanceWeightManager:
    def __init__(self):
        ensure_weights_table()

    def load_or_create(self) -> SignificanceWeights:
        active = self.get_active(allow_missing=True)
        if active:
            return active
        return self._write_defaults()

    def get_active(self, allow_missing: bool = False) -> Optional[SignificanceWeights]:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT * FROM significance_weight_profiles WHERE active=1 ORDER BY version DESC LIMIT 1")
        if row:
            return self._row_to_weights(row)
        if allow_missing:
            return None
        return self._write_defaults()

    def update_event_weight(self, event_type: str, score: float, changed_by: str = "supervisor", reason: str = "manual update", session_uuid: Optional[str] = None) -> SignificanceWeights:
        current = self.load_or_create()
        event_weights = dict(current.event_type_weights)
        event_weights[event_type] = _clamp(score)
        updated = self._save_new_version(current, event_weights, current.severity_modifiers, current.subtype_modifiers, changed_by, reason)
        self._log_change(session_uuid, event_type, event_weights[event_type], changed_by, reason)
        return updated

    def update_subtype_modifier(self, subtype: str, modifier: float, changed_by: str = "supervisor", reason: str = "manual update", session_uuid: Optional[str] = None) -> SignificanceWeights:
        current = self.load_or_create()
        subtype_mods = dict(current.subtype_modifiers)
        subtype_mods[subtype] = max(-1.0, min(1.0, float(modifier)))
        updated = self._save_new_version(current, current.event_type_weights, current.severity_modifiers, subtype_mods, changed_by, reason)
        self._log_change(session_uuid, subtype, subtype_mods[subtype], changed_by, reason)
        return updated

    def version_history(self) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT version, label, active, changed_by, change_reason, created_at FROM significance_weight_profiles ORDER BY version")
        return [dict(r) for r in rows]

    def snapshot(self) -> dict:
        active = self.load_or_create()
        return {"active": active.to_dict(), "history": self.version_history()}

    def _write_defaults(self) -> SignificanceWeights:
        weights = SignificanceWeights(str(uuid.uuid4()), 1, "default", dict(DEFAULT_EVENT_TYPE_WEIGHTS), dict(DEFAULT_SEVERITY_MODIFIERS), dict(DEFAULT_SUBTYPE_MODIFIERS), "system", "initial defaults")
        self._insert(weights, active=True)
        return weights

    def _save_new_version(self, current, event_weights, severity_mods, subtype_mods, changed_by, reason):
        from ..memory.store import get_store
        store = get_store()
        store.execute("UPDATE significance_weight_profiles SET active=0 WHERE active=1")
        weights = SignificanceWeights(str(uuid.uuid4()), int(current.version) + 1, current.label, event_weights, severity_mods, subtype_mods, changed_by, reason)
        self._insert(weights, active=True)
        return weights

    def _insert(self, weights: SignificanceWeights, active: bool):
        from ..memory.store import get_store
        get_store().execute("""
            INSERT INTO significance_weight_profiles
                (profile_id, version, label, event_type_weights, severity_modifiers, subtype_modifiers, active, changed_by, change_reason, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (weights.profile_id, weights.version, weights.label, json.dumps(weights.event_type_weights), json.dumps(weights.severity_modifiers), json.dumps(weights.subtype_modifiers), 1 if active else 0, weights.changed_by, weights.change_reason, weights.created_at, weights.updated_at))
        get_store().commit()

    def _row_to_weights(self, row) -> SignificanceWeights:
        return SignificanceWeights(row["profile_id"], row["version"], row["label"], json.loads(row["event_type_weights"]), json.loads(row["severity_modifiers"]), json.loads(row["subtype_modifiers"]), row["changed_by"], row["change_reason"], row["created_at"], row["updated_at"])

    def _log_change(self, session_uuid, subject, value, changed_by, reason):
        if not session_uuid:
            return
        from ..memory.event_logger import log_event, EventType, Source
        log_event(session_uuid, EventType.CONFIG_CHANGE, f"Significance weight updated for {subject}.", Source.HUMAN, subtype="significance_weight_update", data={"subject": subject, "value": value, "changed_by": changed_by, "reason": reason})
