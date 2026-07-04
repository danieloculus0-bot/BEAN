"""Brain 0.9 wisdom schema and shared constants.

Wisdom is event-triggered associative memory plus repair intelligence.
It tracks pressure and interpretation without pretending emotion.
"""

from __future__ import annotations

FORBIDDEN_EMOTION_PHRASES = [
    "i feel hurt",
    "i feel abandoned",
    "i am sad",
    "i am angry",
    "i love",
    "i miss",
    "i feel close",
    "i am sentient",
    "i have feelings",
]

PRESSURE_DIMENSIONS = [
    "rejection_pressure",
    "abandonment_pressure",
    "shame_pressure",
    "trust_damage",
    "uncertainty_load",
    "contradiction_load",
    "belonging_threat",
    "future_plan_threat",
    "agency_threat",
]

WISDOM_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wisdom_trigger_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    pattern_json TEXT NOT NULL DEFAULT '{}',
    pressure_targets_json TEXT NOT NULL DEFAULT '{}',
    activation_threshold REAL NOT NULL DEFAULT 0.6,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_associations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    association_id TEXT NOT NULL UNIQUE,
    from_type TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    association_type TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0.5,
    confidence REAL NOT NULL DEFAULT 0.5,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    last_activated_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_pressure_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pressure_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    source_event_id INTEGER,
    rejection_pressure REAL NOT NULL DEFAULT 0.0,
    abandonment_pressure REAL NOT NULL DEFAULT 0.0,
    shame_pressure REAL NOT NULL DEFAULT 0.0,
    trust_damage REAL NOT NULL DEFAULT 0.0,
    uncertainty_load REAL NOT NULL DEFAULT 0.0,
    contradiction_load REAL NOT NULL DEFAULT 0.0,
    belonging_threat REAL NOT NULL DEFAULT 0.0,
    future_plan_threat REAL NOT NULL DEFAULT 0.0,
    agency_threat REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_meaning_frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    source_event_id INTEGER,
    event_fact TEXT NOT NULL,
    symbolic_interpretation TEXT,
    assumption_candidate TEXT,
    evidence_for_json TEXT NOT NULL DEFAULT '[]',
    evidence_against_json TEXT NOT NULL DEFAULT '[]',
    alternative_interpretations_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_score REAL NOT NULL DEFAULT 0.5,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_activation_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    source_event_id INTEGER,
    root_trigger TEXT NOT NULL,
    activated_nodes_json TEXT NOT NULL DEFAULT '[]',
    pressure_delta_json TEXT NOT NULL DEFAULT '{}',
    meaning_frame_id TEXT,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_score REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_wound_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wound_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    trigger_signature_json TEXT NOT NULL DEFAULT '{}',
    pressure_signature_json TEXT NOT NULL DEFAULT '{}',
    recurring_interpretations_json TEXT NOT NULL DEFAULT '[]',
    activation_count INTEGER NOT NULL DEFAULT 0,
    unresolved_score REAL NOT NULL DEFAULT 0.5,
    last_activated_at TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_repair_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repair_id TEXT NOT NULL UNIQUE,
    session_uuid TEXT NOT NULL,
    source_event_id INTEGER,
    wound_id TEXT,
    relationship_id TEXT,
    repair_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    action_taken_json TEXT NOT NULL DEFAULT '{}',
    pressure_before_json TEXT NOT NULL DEFAULT '{}',
    pressure_after_json TEXT,
    repair_success REAL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE TABLE IF NOT EXISTS wisdom_loop_signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loop_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    trigger_signature_json TEXT NOT NULL DEFAULT '{}',
    role_a_pattern TEXT,
    role_b_pattern TEXT,
    escalation_pattern TEXT,
    repair_pattern TEXT,
    recurrence_count INTEGER NOT NULL DEFAULT 0,
    repair_success_rate REAL,
    last_seen_at TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
);
"""


def _conn(conn=None):
    if conn is not None:
        return conn
    from ..memory.store import get_store
    return get_store()._conn()


def init_wisdom_schema(conn=None):
    c = _conn(conn)
    c.executescript(WISDOM_SCHEMA_SQL)
    c.commit()
    return c


def no_forbidden_language(text: str) -> bool:
    lowered = (text or "").lower()
    return not any(phrase in lowered for phrase in FORBIDDEN_EMOTION_PHRASES)
