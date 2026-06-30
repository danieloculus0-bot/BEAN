"""Reasoning proposal storage for Brain 0.11.

Reasoning proposals are structured records. They may suggest candidates, but
nothing in this module executes any candidate.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

FORBIDDEN_REASONING_PHRASES = [
    "i am sentient",
    "i have feelings",
    "i feel",
    "i am conscious",
    "i executed",
    "i moved the body",
]

REASONING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS reasoning_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    source_context_json TEXT NOT NULL DEFAULT '{}',
    reasoning_text TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.0,
    provider TEXT NOT NULL DEFAULT 'unknown',
    status TEXT NOT NULL DEFAULT 'pending',
    referenced_hypothesis_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reasoning_action_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL UNIQUE,
    proposal_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    risk_level TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'proposed',
    supervisor_decision TEXT,
    supervisor_id TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reasoning_context_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    context_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn(conn=None):
    if conn is not None:
        return conn
    from ..memory.store import get_store
    return get_store()._conn()


def init_reasoning_schema(conn=None) -> None:
    conn = _conn(conn)
    conn.executescript(REASONING_SCHEMA_SQL)
    # Additive migration for earlier Brain 0.11 drafts.
    try:
        conn.execute("ALTER TABLE reasoning_proposals ADD COLUMN referenced_hypothesis_ids_json TEXT NOT NULL DEFAULT '[]'")
    except Exception:
        pass
    conn.commit()


@dataclass
class ReasoningProposal:
    session_uuid: str
    source_context: dict[str, Any]
    reasoning_text: str
    summary: str
    confidence: float = 0.0
    provider: str = "unknown"
    action_candidates: list[dict[str, Any]] = field(default_factory=list)
    referenced_hypothesis_ids: list[str] = field(default_factory=list)
    status: str = "pending"
    proposal_id: str = field(default_factory=lambda: f"rp_{uuid.uuid4().hex[:16]}")
    created_at: str = field(default_factory=now_utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "session_uuid": self.session_uuid,
            "source_context": self.source_context,
            "reasoning_text": self.reasoning_text,
            "summary": self.summary,
            "confidence": self.confidence,
            "provider": self.provider,
            "action_candidates": self.action_candidates,
            "referenced_hypothesis_ids": self.referenced_hypothesis_ids,
            "status": self.status,
            "created_at": self.created_at,
        }


def check_no_forbidden_reasoning_language(text: str) -> tuple[bool, list[str]]:
    lowered = (text or "").lower()
    hits = [phrase for phrase in FORBIDDEN_REASONING_PHRASES if phrase in lowered]
    return (not hits, hits)


def persist_proposal(conn, proposal: ReasoningProposal) -> str:
    conn = _conn(conn)
    init_reasoning_schema(conn)
    ok, hits = check_no_forbidden_reasoning_language(proposal.reasoning_text + " " + proposal.summary)
    if not ok:
        raise ValueError(f"Forbidden reasoning language: {hits}")
    conn.execute(
        """
        INSERT INTO reasoning_proposals
            (proposal_id, session_uuid, source_context_json, reasoning_text, summary,
             confidence, provider, status, referenced_hypothesis_ids_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposal.proposal_id,
            proposal.session_uuid,
            json.dumps(proposal.source_context),
            proposal.reasoning_text,
            proposal.summary,
            max(0.0, min(1.0, float(proposal.confidence))),
            proposal.provider,
            proposal.status,
            json.dumps(proposal.referenced_hypothesis_ids),
            proposal.created_at,
        ),
    )
    for candidate in proposal.action_candidates:
        candidate_id = str(candidate.get("candidate_id") or f"cand_{uuid.uuid4().hex[:16]}")
        conn.execute(
            """
            INSERT INTO reasoning_action_candidates
                (candidate_id, proposal_id, action_type, rationale, payload_json,
                 risk_level, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                proposal.proposal_id,
                str(candidate.get("action_type", "defer")),
                str(candidate.get("rationale", "")),
                json.dumps(candidate.get("payload") or {}),
                str(candidate.get("risk_level", "medium")),
                "proposed",
                now_utc(),
            ),
        )
    conn.commit()
    return proposal.proposal_id


def get_proposal(conn, proposal_id: str) -> dict[str, Any] | None:
    conn = _conn(conn)
    init_reasoning_schema(conn)
    row = conn.execute("SELECT * FROM reasoning_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    if row is None:
        return None
    candidates = conn.execute("SELECT * FROM reasoning_action_candidates WHERE proposal_id=? ORDER BY id", (proposal_id,)).fetchall()
    return {
        "proposal_id": row["proposal_id"],
        "session_uuid": row["session_uuid"],
        "source_context": json.loads(row["source_context_json"] or "{}"),
        "reasoning_text": row["reasoning_text"],
        "summary": row["summary"],
        "confidence": float(row["confidence"]),
        "provider": row["provider"],
        "status": row["status"],
        "referenced_hypothesis_ids": json.loads(row["referenced_hypothesis_ids_json"] or "[]"),
        "created_at": row["created_at"],
        "action_candidates": [dict(candidate) for candidate in candidates],
    }


def get_pending_proposals(conn=None, limit: int = 25) -> list[dict[str, Any]]:
    conn = _conn(conn)
    init_reasoning_schema(conn)
    rows = conn.execute("SELECT proposal_id FROM reasoning_proposals WHERE status='pending' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [get_proposal(conn, row["proposal_id"]) for row in rows]


def get_pending_candidates(conn=None, limit: int = 25) -> list[dict[str, Any]]:
    conn = _conn(conn)
    init_reasoning_schema(conn)
    rows = conn.execute("SELECT * FROM reasoning_action_candidates WHERE status='proposed' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def decide_action_candidate(conn, candidate_id: str, decision: str, supervisor_id: str = "supervisor") -> dict[str, Any]:
    conn = _conn(conn)
    init_reasoning_schema(conn)
    if decision not in {"accepted", "rejected"}:
        raise ValueError("decision must be accepted or rejected")
    row = conn.execute("SELECT * FROM reasoning_action_candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
    if row is None:
        return {"ok": False, "error": "candidate not found"}
    conn.execute(
        """
        UPDATE reasoning_action_candidates
        SET status=?, supervisor_decision=?, supervisor_id=?, decided_at=?
        WHERE candidate_id=?
        """,
        (decision, decision, supervisor_id, now_utc(), candidate_id),
    )
    conn.commit()
    return {"ok": True, "candidate_id": candidate_id, "decision": decision, "executed": False, "motion_enabled": False}
