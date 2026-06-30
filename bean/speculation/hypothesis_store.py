"""SQLite storage for BEAN speculative hypotheses.

The schema is package-local and idempotent. Records are append-safe: use status
updates, supersession, and archival instead of deletion.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .claim_types import (
    VALID_ACTION_PERMISSIONS,
    VALID_CLAIM_TYPES,
    VALID_EVIDENCE_LEVELS,
    VALID_HYPOTHESIS_STATUSES,
)
from .evidence import EvidenceLink
from .hypothesis import HypothesisRecord

SPECULATION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS speculative_hypotheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    evidence_level TEXT NOT NULL DEFAULT 'unknown',
    confidence REAL NOT NULL DEFAULT 0.3,
    supporting_evidence_json TEXT NOT NULL DEFAULT '[]',
    contradicting_evidence_json TEXT NOT NULL DEFAULT '[]',
    falsification_path TEXT NOT NULL DEFAULT '',
    resolution_path TEXT NOT NULL DEFAULT '',
    action_permission TEXT NOT NULL DEFAULT 'forbidden_for_action',
    source TEXT NOT NULL DEFAULT 'unknown',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    superseded_by TEXT
);

CREATE TABLE IF NOT EXISTS speculative_evidence_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id TEXT NOT NULL UNIQUE,
    hypothesis_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT,
    polarity TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS speculative_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL UNIQUE,
    hypothesis_id TEXT NOT NULL,
    reviewer TEXT NOT NULL DEFAULT 'system',
    review_type TEXT NOT NULL DEFAULT 'automated',
    previous_status TEXT,
    new_status TEXT,
    previous_evidence_level TEXT,
    new_evidence_level TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn(obj=None):
    if obj is not None:
        return obj
    from ..memory.store import get_store
    return get_store()._conn()


def init_speculation_schema(conn=None) -> None:
    conn = _conn(conn)
    conn.executescript(SPECULATION_SCHEMA_SQL)
    conn.commit()


def _validate_record(record: HypothesisRecord) -> None:
    if record.claim_type not in VALID_CLAIM_TYPES:
        raise ValueError(f"Invalid claim_type: {record.claim_type!r}")
    if record.evidence_level not in VALID_EVIDENCE_LEVELS:
        raise ValueError(f"Invalid evidence_level: {record.evidence_level!r}")
    if record.action_permission not in VALID_ACTION_PERMISSIONS:
        raise ValueError(f"Invalid action_permission: {record.action_permission!r}")
    if record.status not in VALID_HYPOTHESIS_STATUSES:
        raise ValueError(f"Invalid status: {record.status!r}")


def persist_hypothesis(conn, record: HypothesisRecord) -> str:
    conn = _conn(conn)
    init_speculation_schema(conn)
    _validate_record(record)
    conn.execute(
        """
        INSERT INTO speculative_hypotheses
            (hypothesis_id, session_uuid, claim_text, claim_type, evidence_level,
             confidence, supporting_evidence_json, contradicting_evidence_json,
             falsification_path, resolution_path, action_permission, source,
             status, created_at, updated_at, superseded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.hypothesis_id,
            record.session_uuid,
            record.claim_text,
            record.claim_type,
            record.evidence_level,
            record.confidence,
            json.dumps(record.supporting_evidence),
            json.dumps(record.contradicting_evidence),
            record.falsification_path,
            record.resolution_path,
            record.action_permission,
            record.source,
            record.status,
            record.created_at,
            record.updated_at,
            record.superseded_by,
        ),
    )
    conn.commit()
    return record.hypothesis_id


def _row_to_dict(row) -> dict[str, Any]:
    keys = row.keys() if hasattr(row, "keys") else []
    return {
        "hypothesis_id": row["hypothesis_id"],
        "session_uuid": row["session_uuid"],
        "claim_text": row["claim_text"],
        "claim_type": row["claim_type"],
        "evidence_level": row["evidence_level"],
        "confidence": float(row["confidence"]),
        "supporting_evidence": json.loads(row["supporting_evidence_json"] or "[]"),
        "contradicting_evidence": json.loads(row["contradicting_evidence_json"] or "[]"),
        "falsification_path": row["falsification_path"],
        "resolution_path": row["resolution_path"],
        "action_permission": row["action_permission"],
        "source": row["source"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "superseded_by": row["superseded_by"] if "superseded_by" in keys else None,
    }


def get_hypothesis(conn, hypothesis_id: str) -> dict[str, Any] | None:
    conn = _conn(conn)
    init_speculation_schema(conn)
    row = conn.execute("SELECT * FROM speculative_hypotheses WHERE hypothesis_id=?", (hypothesis_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_open_hypotheses(conn, session_uuid: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    conn = _conn(conn)
    init_speculation_schema(conn)
    if session_uuid:
        rows = conn.execute(
            """
            SELECT * FROM speculative_hypotheses
            WHERE status='open' AND session_uuid=?
            ORDER BY id DESC LIMIT ?
            """,
            (session_uuid, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM speculative_hypotheses WHERE status='open' ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_by_claim_type(conn, claim_type: str, limit: int = 25) -> list[dict[str, Any]]:
    if claim_type not in VALID_CLAIM_TYPES:
        raise ValueError(f"Invalid claim_type: {claim_type!r}")
    conn = _conn(conn)
    init_speculation_schema(conn)
    rows = conn.execute(
        "SELECT * FROM speculative_hypotheses WHERE claim_type=? ORDER BY id DESC LIMIT ?",
        (claim_type, limit),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_by_status(conn, status: str, limit: int = 50) -> list[dict[str, Any]]:
    if status not in VALID_HYPOTHESIS_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")
    conn = _conn(conn)
    init_speculation_schema(conn)
    rows = conn.execute(
        "SELECT * FROM speculative_hypotheses WHERE status=? ORDER BY id DESC LIMIT ?",
        (status, limit),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def update_hypothesis_status(conn, hypothesis_id: str, new_status: str, evidence_level: str | None = None, confidence: float | None = None) -> dict[str, Any]:
    if new_status not in VALID_HYPOTHESIS_STATUSES:
        raise ValueError(f"Invalid status: {new_status!r}")
    if evidence_level is not None and evidence_level not in VALID_EVIDENCE_LEVELS:
        raise ValueError(f"Invalid evidence_level: {evidence_level!r}")
    conn = _conn(conn)
    init_speculation_schema(conn)
    existing = get_hypothesis(conn, hypothesis_id)
    if existing is None:
        raise ValueError(f"Hypothesis not found: {hypothesis_id}")
    next_level = evidence_level or existing["evidence_level"]
    next_confidence = existing["confidence"] if confidence is None else max(0.0, min(1.0, float(confidence)))
    conn.execute(
        """
        UPDATE speculative_hypotheses
        SET status=?, evidence_level=?, confidence=?, updated_at=?
        WHERE hypothesis_id=?
        """,
        (new_status, next_level, next_confidence, now_utc(), hypothesis_id),
    )
    conn.commit()
    return get_hypothesis(conn, hypothesis_id)


def supersede_hypothesis(conn, old_hypothesis_id: str, new_record: HypothesisRecord) -> dict[str, str]:
    conn = _conn(conn)
    init_speculation_schema(conn)
    old = get_hypothesis(conn, old_hypothesis_id)
    if old is None:
        raise ValueError(f"Hypothesis not found: {old_hypothesis_id}")
    new_id = persist_hypothesis(conn, new_record)
    conn.execute(
        "UPDATE speculative_hypotheses SET status='superseded', superseded_by=?, updated_at=? WHERE hypothesis_id=?",
        (new_id, now_utc(), old_hypothesis_id),
    )
    conn.commit()
    return {"old_hypothesis_id": old_hypothesis_id, "new_hypothesis_id": new_id}


def add_evidence_link(conn, link: EvidenceLink) -> str:
    conn = _conn(conn)
    init_speculation_schema(conn)
    conn.execute(
        """
        INSERT INTO speculative_evidence_links
            (link_id, hypothesis_id, source_type, source_id, polarity, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (link.link_id, link.hypothesis_id, link.source_type, link.source_id, link.polarity, link.note, link.created_at),
    )
    hyp = get_hypothesis(conn, link.hypothesis_id)
    if hyp:
        field = "supporting_evidence_json" if link.polarity == "supporting" else "contradicting_evidence_json"
        current = hyp["supporting_evidence"] if link.polarity == "supporting" else hyp["contradicting_evidence"]
        current.append(link.to_dict())
        conn.execute(
            f"UPDATE speculative_hypotheses SET {field}=?, updated_at=? WHERE hypothesis_id=?",
            (json.dumps(current), now_utc(), link.hypothesis_id),
        )
    conn.commit()
    return link.link_id


def record_review(conn, hypothesis_id: str, reviewer: str = "system", review_type: str = "automated", new_status: str | None = None, new_evidence_level: str | None = None, notes: str = "") -> str:
    conn = _conn(conn)
    init_speculation_schema(conn)
    existing = get_hypothesis(conn, hypothesis_id)
    if existing is None:
        raise ValueError(f"Hypothesis not found: {hypothesis_id}")
    review_id = f"rev_{uuid.uuid4().hex[:16]}"
    conn.execute(
        """
        INSERT INTO speculative_reviews
            (review_id, hypothesis_id, reviewer, review_type, previous_status,
             new_status, previous_evidence_level, new_evidence_level, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review_id,
            hypothesis_id,
            reviewer,
            review_type,
            existing["status"],
            new_status or existing["status"],
            existing["evidence_level"],
            new_evidence_level or existing["evidence_level"],
            notes,
            now_utc(),
        ),
    )
    conn.commit()
    if new_status is not None or new_evidence_level is not None:
        update_hypothesis_status(conn, hypothesis_id, new_status or existing["status"], evidence_level=new_evidence_level)
    return review_id


def count_by_status(conn=None) -> dict[str, int]:
    conn = _conn(conn)
    init_speculation_schema(conn)
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM speculative_hypotheses GROUP BY status").fetchall()
    return {row["status"]: int(row["n"]) for row in rows}


def count_all(conn=None) -> dict[str, int]:
    conn = _conn(conn)
    init_speculation_schema(conn)
    total = conn.execute("SELECT COUNT(*) AS n FROM speculative_hypotheses").fetchone()["n"]
    reviews = conn.execute("SELECT COUNT(*) AS n FROM speculative_reviews").fetchone()["n"]
    statuses = count_by_status(conn)
    return {
        "speculative_hypotheses": int(total),
        "open_hypotheses": int(statuses.get("open", 0)),
        "contradicted_hypotheses": int(statuses.get("contradicted", 0)),
        "resolved_hypotheses": int(statuses.get("resolved", 0)),
        "speculation_reviews": int(reviews),
    }
