"""SQLite store for Brain 0.13 hypotheses."""

import json
import uuid

from .claim_types import VALID_ACTION_PERMISSIONS, VALID_CLAIM_TYPES, VALID_EVIDENCE_LEVELS, VALID_HYPOTHESIS_STATUSES
from .hypothesis import HypothesisRecord

SCHEMA = """
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
 created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
 updated_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
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
 created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
CREATE TABLE IF NOT EXISTS speculative_reviews (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 review_id TEXT NOT NULL UNIQUE,
 hypothesis_id TEXT NOT NULL,
 reviewer TEXT NOT NULL DEFAULT 'system',
 review_type TEXT NOT NULL DEFAULT 'automated',
 previous_status TEXT,
 new_status TEXT,
 notes TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


def init_speculation_schema(conn=None):
    if conn is None:
        from ..memory.store import get_store
        conn = get_store()._conn()
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def persist_hypothesis(conn, record: HypothesisRecord) -> str:
    if record.claim_type not in VALID_CLAIM_TYPES or record.evidence_level not in VALID_EVIDENCE_LEVELS or record.action_permission not in VALID_ACTION_PERMISSIONS or record.status not in VALID_HYPOTHESIS_STATUSES:
        raise ValueError("invalid hypothesis vocabulary")
    conn.execute("INSERT INTO speculative_hypotheses (hypothesis_id, session_uuid, claim_text, claim_type, evidence_level, confidence, supporting_evidence_json, contradicting_evidence_json, falsification_path, resolution_path, action_permission, source, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (record.hypothesis_id, record.session_uuid, record.claim_text, record.claim_type, record.evidence_level, record.confidence, json.dumps(record.supporting_evidence), json.dumps(record.contradicting_evidence), record.falsification_path, record.resolution_path, record.action_permission, record.source, record.status))
    conn.commit()
    return record.hypothesis_id


def _row(row):
    if not row: return None
    d = dict(row)
    d["supporting_evidence"] = json.loads(d.pop("supporting_evidence_json"))
    d["contradicting_evidence"] = json.loads(d.pop("contradicting_evidence_json"))
    return d


def get_hypothesis(conn, hypothesis_id: str):
    return _row(conn.execute("SELECT * FROM speculative_hypotheses WHERE hypothesis_id=?", (hypothesis_id,)).fetchone())


def list_open_hypotheses(conn, session_uuid=None, limit=25):
    if session_uuid:
        rows = conn.execute("SELECT * FROM speculative_hypotheses WHERE status='open' AND session_uuid=? ORDER BY id DESC LIMIT ?", (session_uuid, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM speculative_hypotheses WHERE status='open' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def update_hypothesis_status(conn, hypothesis_id: str, new_status: str, evidence_level=None):
    if new_status not in VALID_HYPOTHESIS_STATUSES:
        raise ValueError("invalid status")
    if evidence_level:
        conn.execute("UPDATE speculative_hypotheses SET status=?, evidence_level=?, updated_at=datetime('now','utc') WHERE hypothesis_id=?", (new_status, evidence_level, hypothesis_id))
    else:
        conn.execute("UPDATE speculative_hypotheses SET status=?, updated_at=datetime('now','utc') WHERE hypothesis_id=?", (new_status, hypothesis_id))
    conn.commit()
    return get_hypothesis(conn, hypothesis_id)


def record_review(conn, hypothesis_id: str, reviewer="system", review_type="automated", new_status=None, notes=""):
    old = get_hypothesis(conn, hypothesis_id)
    rid = f"rev_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO speculative_reviews (review_id, hypothesis_id, reviewer, review_type, previous_status, new_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)", (rid, hypothesis_id, reviewer, review_type, old.get("status") if old else None, new_status or (old.get("status") if old else None), notes))
    conn.commit()
    if new_status:
        update_hypothesis_status(conn, hypothesis_id, new_status)
    return rid


def count_by_status(conn):
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM speculative_hypotheses GROUP BY status").fetchall()
    return {r["status"]: r["n"] for r in rows}
