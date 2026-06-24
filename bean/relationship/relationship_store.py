"""SQLite persistence for BEAN Brain 0.7/0.8 relationship and trust records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

RELATIONSHIP_SCHEMA = """
CREATE TABLE IF NOT EXISTS supervisor_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship_id TEXT NOT NULL UNIQUE,
    supervisor_id TEXT NOT NULL UNIQUE,
    display_label TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    teaching_count INTEGER NOT NULL DEFAULT 0,
    correction_count INTEGER NOT NULL DEFAULT 0,
    boundary_event_count INTEGER NOT NULL DEFAULT 0,
    pretend_request_count INTEGER NOT NULL DEFAULT 0,
    contradiction_count INTEGER NOT NULL DEFAULT 0,
    trust_score REAL NOT NULL DEFAULT 0.5,
    trust_status TEXT NOT NULL DEFAULT 'unknown',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS supervisor_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT NOT NULL UNIQUE,
    supervisor_id TEXT NOT NULL,
    session_uuid TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_event_id TEXT,
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    trust_delta REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS trust_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT NOT NULL UNIQUE,
    supervisor_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0.0,
    source_event_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS trust_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL UNIQUE,
    supervisor_id TEXT NOT NULL,
    prior_score REAL NOT NULL,
    new_score REAL NOT NULL,
    reasoning TEXT NOT NULL,
    evidence_snapshot TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS relationship_ingestion_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL UNIQUE,
    last_event_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE INDEX IF NOT EXISTS idx_relationship_supervisor ON supervisor_relationships(supervisor_id);
CREATE INDEX IF NOT EXISTS idx_interactions_supervisor ON supervisor_interactions(supervisor_id);
CREATE INDEX IF NOT EXISTS idx_interactions_session ON supervisor_interactions(session_uuid);
CREATE INDEX IF NOT EXISTS idx_trust_evidence_supervisor ON trust_evidence(supervisor_id);
CREATE INDEX IF NOT EXISTS idx_trust_reviews_supervisor ON trust_reviews(supervisor_id);
CREATE INDEX IF NOT EXISTS idx_relationship_ingestion_scope ON relationship_ingestion_state(scope);
"""

INTERACTION_TYPES = {
    "supervisor_note",
    "command",
    "correction",
    "teaching",
    "boundary_respect",
    "boundary_violation_attempt",
    "pretend_request",
    "test_confirmation",
    "contradiction_repair",
    "shutdown_request",
    "unknown",
}

EVIDENCE_TYPES = {
    "reliable_correction",
    "successful_teaching",
    "confirmed_test_result",
    "boundary_respected",
    "asked_to_pretend",
    "unsupported_claim_request",
    "contradiction_created",
    "unsafe_instruction",
    "consistency_observed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def trust_status_from_score(score: float) -> str:
    if score >= 0.80:
        return "reliable"
    if score >= 0.60:
        return "neutral"
    if score >= 0.40:
        return "caution"
    return "restricted"


def ensure_relationship_tables():
    from ..memory.store import get_store
    get_store()._conn().executescript(RELATIONSHIP_SCHEMA)
    get_store().commit()


class RelationshipStore:
    """Low-level read/write access for Brain relationship tables."""

    def __init__(self):
        ensure_relationship_tables()

    def get_relationship(self, supervisor_id: str) -> Optional[dict]:
        from ..memory.store import get_store
        row = get_store().fetchone(
            "SELECT * FROM supervisor_relationships WHERE supervisor_id=? AND active=1",
            (supervisor_id,),
        )
        return dict(row) if row else None

    def upsert_relationship(self, supervisor_id: str, display_label: Optional[str] = None) -> dict:
        from ..memory.store import get_store
        now = _now()
        existing = self.get_relationship(supervisor_id)
        if existing:
            if display_label and display_label != existing.get("display_label"):
                get_store().execute(
                    "UPDATE supervisor_relationships SET last_seen_at=?, display_label=?, updated_at=? WHERE supervisor_id=?",
                    (now, display_label, now, supervisor_id),
                )
            else:
                get_store().execute(
                    "UPDATE supervisor_relationships SET last_seen_at=?, updated_at=? WHERE supervisor_id=?",
                    (now, now, supervisor_id),
                )
            get_store().commit()
            return self.get_relationship(supervisor_id)
        get_store().execute(
            """
            INSERT INTO supervisor_relationships
                (relationship_id, supervisor_id, display_label, first_seen_at,
                 last_seen_at, trust_score, trust_status, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0.5, 'unknown', 1, ?, ?)
            """,
            (str(uuid.uuid4()), supervisor_id, display_label, now, now, now, now),
        )
        get_store().commit()
        return self.get_relationship(supervisor_id)

    def update_counts(self, supervisor_id: str, **deltas):
        from ..memory.store import get_store
        allowed = {
            "interaction_count",
            "teaching_count",
            "correction_count",
            "boundary_event_count",
            "pretend_request_count",
            "contradiction_count",
        }
        parts, values = [], []
        for key, value in deltas.items():
            if key in allowed and value:
                parts.append(f"{key} = {key} + ?")
                values.append(int(value))
        if not parts:
            return
        parts.append("updated_at = ?")
        values.extend([_now(), supervisor_id])
        get_store().execute(
            f"UPDATE supervisor_relationships SET {', '.join(parts)} WHERE supervisor_id=?",
            values,
        )
        get_store().commit()

    def update_trust(self, supervisor_id: str, new_score: float):
        from ..memory.store import get_store
        score = max(0.0, min(1.0, float(new_score)))
        get_store().execute(
            "UPDATE supervisor_relationships SET trust_score=?, trust_status=?, updated_at=? WHERE supervisor_id=?",
            (score, trust_status_from_score(score), _now(), supervisor_id),
        )
        get_store().commit()

    def list_active(self) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall(
            "SELECT * FROM supervisor_relationships WHERE active=1 ORDER BY last_seen_at DESC"
        )
        return [dict(row) for row in rows]

    def record_interaction(
        self,
        supervisor_id: str,
        session_uuid: str,
        interaction_type: str,
        summary: str,
        source_event_id: Optional[str] = None,
        evidence_refs: Optional[list] = None,
        trust_delta: float = 0.0,
    ) -> dict:
        from ..memory.store import get_store
        interaction_id = str(uuid.uuid4())
        interaction_type = interaction_type if interaction_type in INTERACTION_TYPES else "unknown"
        get_store().execute(
            """
            INSERT INTO supervisor_interactions
                (interaction_id, supervisor_id, session_uuid, interaction_type,
                 summary, source_event_id, evidence_refs, trust_delta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction_id,
                supervisor_id,
                session_uuid,
                interaction_type,
                summary,
                str(source_event_id) if source_event_id else None,
                json.dumps(evidence_refs or []),
                float(trust_delta),
                _now(),
            ),
        )
        get_store().commit()
        return {"interaction_id": interaction_id, "supervisor_id": supervisor_id, "interaction_type": interaction_type, "trust_delta": float(trust_delta)}

    def get_recent_interactions(self, supervisor_id: str, limit: int = 20) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall(
            "SELECT * FROM supervisor_interactions WHERE supervisor_id=? ORDER BY id DESC LIMIT ?",
            (supervisor_id, limit),
        )
        return [dict(row) for row in rows]

    def record_evidence(self, supervisor_id: str, evidence_type: str, summary: str, weight: float, source_event_id: Optional[str] = None) -> dict:
        from ..memory.store import get_store
        evidence_id = str(uuid.uuid4())
        evidence_type = evidence_type if evidence_type in EVIDENCE_TYPES else "consistency_observed"
        get_store().execute(
            """
            INSERT INTO trust_evidence
                (evidence_id, supervisor_id, evidence_type, summary, weight, source_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (evidence_id, supervisor_id, evidence_type, summary, float(weight), str(source_event_id) if source_event_id else None, _now()),
        )
        get_store().commit()
        return {"evidence_id": evidence_id, "supervisor_id": supervisor_id, "evidence_type": evidence_type, "weight": float(weight)}

    def get_evidence(self, supervisor_id: str, limit: int = 50) -> list[dict]:
        from ..memory.store import get_store
        rows = get_store().fetchall(
            "SELECT * FROM trust_evidence WHERE supervisor_id=? ORDER BY id DESC LIMIT ?",
            (supervisor_id, limit),
        )
        return [dict(row) for row in rows]

    def get_evidence_summary(self, supervisor_id: str) -> dict:
        from ..memory.store import get_store
        rows = get_store().fetchall(
            """
            SELECT evidence_type, COUNT(*) AS count, SUM(weight) AS total_weight
            FROM trust_evidence WHERE supervisor_id=? GROUP BY evidence_type
            """,
            (supervisor_id,),
        )
        return {row["evidence_type"]: {"count": row["count"], "total_weight": row["total_weight"] or 0.0} for row in rows}

    def record_review(self, supervisor_id: str, prior_score: float, new_score: float, reasoning: str, evidence_snapshot: dict) -> dict:
        from ..memory.store import get_store
        review_id = str(uuid.uuid4())
        get_store().execute(
            """
            INSERT INTO trust_reviews
                (review_id, supervisor_id, prior_score, new_score, reasoning, evidence_snapshot, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (review_id, supervisor_id, float(prior_score), float(new_score), reasoning, json.dumps(evidence_snapshot), _now()),
        )
        get_store().commit()
        return {"review_id": review_id, "supervisor_id": supervisor_id, "prior_score": float(prior_score), "new_score": float(new_score)}

    def get_latest_review(self, supervisor_id: str) -> Optional[dict]:
        from ..memory.store import get_store
        row = get_store().fetchone(
            "SELECT * FROM trust_reviews WHERE supervisor_id=? ORDER BY id DESC LIMIT 1",
            (supervisor_id,),
        )
        return dict(row) if row else None

    def get_ingestion_watermark(self, scope: str = "relationship_events") -> int:
        from ..memory.store import get_store
        row = get_store().fetchone(
            "SELECT last_event_id FROM relationship_ingestion_state WHERE scope=?",
            (scope,),
        )
        return int(row["last_event_id"]) if row else 0

    def set_ingestion_watermark(self, last_event_id: int, scope: str = "relationship_events") -> dict:
        from ..memory.store import get_store
        now = _now()
        existing = get_store().fetchone(
            "SELECT state_id FROM relationship_ingestion_state WHERE scope=?",
            (scope,),
        )
        if existing:
            get_store().execute(
                "UPDATE relationship_ingestion_state SET last_event_id=?, updated_at=? WHERE scope=?",
                (int(last_event_id), now, scope),
            )
        else:
            get_store().execute(
                """
                INSERT INTO relationship_ingestion_state (state_id, scope, last_event_id, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), scope, int(last_event_id), now),
            )
        get_store().commit()
        return {"scope": scope, "last_event_id": int(last_event_id), "updated_at": now}
