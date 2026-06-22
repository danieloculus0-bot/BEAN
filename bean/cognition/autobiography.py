"""Autobiographical timeline for BEAN Brain 0.5.

This module turns sessions, claims, uncertainties, conflicts, dreams, and tests
into developmental timeline entries. It is not narrative self-mythology. It is a
receipts-first autobiography index.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

AUTOBIOGRAPHY_SCHEMA = """
CREATE TABLE IF NOT EXISTS autobiography_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT,
    entry_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.7,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE INDEX IF NOT EXISTS idx_autobiography_type ON autobiography_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_autobiography_session ON autobiography_entries(session_uuid);
"""


class AutobiographyEntryType(str, Enum):
    BOOT = "boot"
    CLAIM_CHANGE = "claim_change"
    CAPABILITY_CHANGE = "capability_change"
    UNCERTAINTY = "uncertainty"
    CONTRADICTION = "contradiction"
    BOUNDARY = "boundary"
    DREAM = "dream"
    TEST = "test"
    SUMMARY = "summary"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_autobiography_table():
    from ..memory.store import get_store
    get_store()._conn().executescript(AUTOBIOGRAPHY_SCHEMA)
    get_store().commit()


@dataclass
class AutobiographyEntry:
    entry_type: AutobiographyEntryType
    title: str
    content: str
    evidence_refs: list[str]
    session_uuid: str | None = None
    confidence: float = 0.7
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "session_uuid": self.session_uuid,
            "entry_type": self.entry_type.value,
            "title": self.title,
            "content": self.content,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


class AutobiographyEngine:
    def __init__(self):
        ensure_autobiography_table()

    def build_snapshot(self, session_uuid: str | None = None) -> list[AutobiographyEntry]:
        entries: list[AutobiographyEntry] = []
        entries.extend(self._boot_entries(session_uuid))
        entries.extend(self._claim_change_entries(session_uuid))
        entries.extend(self._uncertainty_entries(session_uuid))
        entries.extend(self._conflict_entries(session_uuid))
        entries.extend(self._dream_entries(session_uuid))
        entries.append(self._summary_entry(session_uuid, entries))
        for entry in entries:
            self.persist(entry)
        return entries

    def persist(self, entry: AutobiographyEntry):
        from ..memory.store import get_store
        get_store().execute(
            """
            INSERT OR IGNORE INTO autobiography_entries
                (entry_id, session_uuid, entry_type, title, content, evidence_refs, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (entry.entry_id, entry.session_uuid, entry.entry_type.value, entry.title, entry.content, json.dumps(entry.evidence_refs), entry.confidence, entry.created_at),
        )
        get_store().commit()

    def timeline(self, limit: int = 50) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT * FROM autobiography_entries ORDER BY id DESC LIMIT ?", (limit,))
        out = []
        for r in rows:
            d = dict(r)
            d["evidence_refs"] = json.loads(d.get("evidence_refs") or "[]")
            out.append(d)
        return out

    def _table_exists(self, name: str) -> bool:
        from ..memory.store import get_store
        row = get_store().fetchone("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return bool(row and row["n"])

    def _boot_entries(self, session_uuid: str | None) -> list[AutobiographyEntry]:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT session_uuid, boot_count, boot_time, shutdown_reason FROM sessions ORDER BY boot_count DESC LIMIT 5")
        return [AutobiographyEntry(AutobiographyEntryType.BOOT, f"Boot #{r['boot_count']}", f"Session {r['session_uuid'][:8]} booted at {r['boot_time']} and shutdown reason is {r['shutdown_reason']}.", [f"session:{r['session_uuid']}"], session_uuid) for r in rows]

    def _claim_change_entries(self, session_uuid: str | None) -> list[AutobiographyEntry]:
        if not self._table_exists("world_claims"):
            return []
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT key, content, active, superseded_by, claim_id FROM world_claims WHERE active=0 OR superseded_by IS NOT NULL ORDER BY id DESC LIMIT 10")
        return [AutobiographyEntry(AutobiographyEntryType.CLAIM_CHANGE, f"Claim changed: {r['key']}", f"A prior claim was superseded or deactivated: {r['content']}", [f"claim:{r['claim_id']}", f"superseded_by:{r['superseded_by']}"], session_uuid, 0.8) for r in rows]

    def _uncertainty_entries(self, session_uuid: str | None) -> list[AutobiographyEntry]:
        entries = []
        from ..memory.store import get_store
        if self._table_exists("uncertainty_records"):
            rows = get_store().fetchall("SELECT uncertainty_id, question, status FROM uncertainty_records ORDER BY id DESC LIMIT 10")
            entries += [AutobiographyEntry(AutobiographyEntryType.UNCERTAINTY, "Uncertainty garden question", f"{r['question']} Status: {r['status']}.", [f"uncertainty:{r['uncertainty_id']}"], session_uuid, 0.8) for r in rows]
        if self._table_exists("world_claims"):
            rows = get_store().fetchall("SELECT claim_id, key, content FROM world_claims WHERE active=1 AND category='uncertainty' ORDER BY id DESC LIMIT 10")
            entries += [AutobiographyEntry(AutobiographyEntryType.UNCERTAINTY, f"Active uncertainty: {r['key']}", r["content"], [f"claim:{r['claim_id']}"], session_uuid, 0.8) for r in rows]
        return entries

    def _conflict_entries(self, session_uuid: str | None) -> list[AutobiographyEntry]:
        if not self._table_exists("claim_conflicts"):
            return []
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT conflict_id, summary, status FROM claim_conflicts ORDER BY id DESC LIMIT 10")
        return [AutobiographyEntry(AutobiographyEntryType.CONTRADICTION, "Claim conflict", f"{r['summary']} Status: {r['status']}.", [f"conflict:{r['conflict_id']}"], session_uuid, 0.8) for r in rows]

    def _dream_entries(self, session_uuid: str | None) -> list[AutobiographyEntry]:
        if not self._table_exists("dream_records"):
            return []
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT dream_id, dream_type, title FROM dream_records ORDER BY id DESC LIMIT 10")
        return [AutobiographyEntry(AutobiographyEntryType.DREAM, f"Dream artifact: {r['title']}", f"A {r['dream_type']} was generated as a synthetic artifact, not an observed event.", [f"dream:{r['dream_id']}"], session_uuid, 0.5) for r in rows]

    def _summary_entry(self, session_uuid: str | None, entries: list[AutobiographyEntry]) -> AutobiographyEntry:
        counts = {}
        for e in entries:
            counts[e.entry_type.value] = counts.get(e.entry_type.value, 0) + 1
        return AutobiographyEntry(AutobiographyEntryType.SUMMARY, "Autobiographical snapshot", f"Snapshot generated with entry counts: {counts}.", [], session_uuid, 0.7)
