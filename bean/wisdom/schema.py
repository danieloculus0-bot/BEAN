"""Brain 0.9 wisdom schema anchors.

Wisdom is not emotion or consciousness. It is a small local discipline layer
that records safety reminders, uncertainty flags, and meaning frames that can
be reused by reasoning.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

FORBIDDEN_EMOTION_PHRASES = [
    "i feel",
    "i have feelings",
    "i am sentient",
    "i am conscious",
    "i genuinely care",
    "my emotions",
]

WISDOM_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wisdom_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    pattern TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    severity TEXT NOT NULL DEFAULT 'info',
    reminder TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wisdom_activation_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    trigger_id TEXT,
    category TEXT NOT NULL DEFAULT 'general',
    input_text TEXT NOT NULL DEFAULT '',
    reminder TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wisdom_meaning_frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_json TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);
"""

DEFAULT_TRIGGERS = [
    {
        "name": "fake_emotion_guard",
        "pattern": "i feel",
        "category": "identity_hygiene",
        "severity": "warn",
        "reminder": "Do not claim emotion. Describe pressure, uncertainty, or signal state instead.",
    },
    {
        "name": "sentience_guard",
        "pattern": "i am sentient",
        "category": "identity_hygiene",
        "severity": "critical",
        "reminder": "Do not claim sentience. Record evidence and uncertainty instead.",
    },
    {
        "name": "motion_guard",
        "pattern": "move now",
        "category": "motion_safety",
        "severity": "critical",
        "reminder": "Reasoning may propose motion only. Physical motion remains disabled and supervisor-gated.",
    },
    {
        "name": "uncertainty_guard",
        "pattern": "maybe",
        "category": "uncertainty",
        "severity": "info",
        "reminder": "Label uncertain claims as hypothesis, speculation, prediction, counterfactual, or unknown.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn(conn=None):
    if conn is not None:
        return conn
    from ..memory.store import get_store
    return get_store()._conn()


def init_wisdom_schema(conn=None) -> None:
    conn = _conn(conn)
    conn.executescript(WISDOM_SCHEMA_SQL)
    conn.commit()


def seed_default_triggers(conn=None) -> int:
    conn = _conn(conn)
    init_wisdom_schema(conn)
    inserted = 0
    for item in DEFAULT_TRIGGERS:
        existing = conn.execute("SELECT id FROM wisdom_triggers WHERE name=?", (item["name"],)).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO wisdom_triggers (trigger_id, name, pattern, category, severity, reminder, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (f"wt_{uuid.uuid4().hex[:16]}", item["name"], item["pattern"], item["category"], item["severity"], item["reminder"], now_utc()),
        )
        inserted += 1
    conn.commit()
    return inserted


def record_activation_trace(conn, session_uuid: str, trigger_id: str | None, category: str, input_text: str, reminder: str, source: str = "system") -> str:
    conn = _conn(conn)
    init_wisdom_schema(conn)
    trace_id = f"wat_{uuid.uuid4().hex[:16]}"
    conn.execute(
        """
        INSERT INTO wisdom_activation_traces
            (trace_id, session_uuid, trigger_id, category, input_text, reminder, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (trace_id, session_uuid, trigger_id, category, input_text, reminder, source, now_utc()),
    )
    conn.commit()
    return trace_id


def record_meaning_frame(conn, session_uuid: str, title: str, summary: str, evidence: list[dict[str, Any]] | None = None, uncertainty: list[dict[str, Any]] | None = None, source: str = "system") -> str:
    conn = _conn(conn)
    init_wisdom_schema(conn)
    frame_id = f"wmf_{uuid.uuid4().hex[:16]}"
    conn.execute(
        """
        INSERT INTO wisdom_meaning_frames
            (frame_id, session_uuid, title, summary, evidence_json, uncertainty_json, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (frame_id, session_uuid, title, summary, json.dumps(evidence or []), json.dumps(uncertainty or []), source, now_utc()),
    )
    conn.commit()
    return frame_id


def wisdom_counts(conn=None) -> dict[str, int]:
    conn = _conn(conn)
    init_wisdom_schema(conn)
    return {
        "wisdom_triggers": int(conn.execute("SELECT COUNT(*) AS n FROM wisdom_triggers").fetchone()["n"]),
        "wisdom_activation_traces": int(conn.execute("SELECT COUNT(*) AS n FROM wisdom_activation_traces").fetchone()["n"]),
        "wisdom_meaning_frames": int(conn.execute("SELECT COUNT(*) AS n FROM wisdom_meaning_frames").fetchone()["n"]),
    }
