-- BEAN Memory Core Schema
-- Version: 0.1.0
-- Philosophy: boring, inspectable, hard to bullshit.
-- Every table has a created_at. Nothing is deleted, only superseded.
-- If it didn't happen in a row, it didn't happen.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─────────────────────────────────────────────
-- IDENTITY
-- What BEAN is right now. One row, versioned.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS identity (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
    name                TEXT    NOT NULL DEFAULT 'BEAN',
    version             TEXT    NOT NULL,           -- schema + software version
    developmental_stage TEXT    NOT NULL,           -- e.g. "memory-core-0.1"
    hardware_body       TEXT    NOT NULL,           -- JSON description of physical body
    what_bean_is        TEXT    NOT NULL,           -- plain language: what this system is
    what_bean_is_not    TEXT    NOT NULL,           -- plain language: explicit disavowals
    created_at          TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- CONTINUITY
-- Boot/shutdown/session history. Survival record.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid    TEXT    NOT NULL UNIQUE,
    boot_time       TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    shutdown_time   TEXT,                           -- NULL means still running
    shutdown_reason TEXT,                           -- clean / error / power_loss / supervisor
    boot_count      INTEGER NOT NULL,               -- monotonically increasing
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- EVENTS
-- Append-only. Core truth. Never delete rows.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid    TEXT    NOT NULL,
    event_uuid      TEXT    NOT NULL UNIQUE,
    event_type      TEXT    NOT NULL,   -- see EventType enum in event_logger.py
    subtype         TEXT,               -- optional finer grain
    summary         TEXT    NOT NULL,   -- human-readable one-liner
    data            TEXT,               -- JSON blob, optional structured payload
    source          TEXT    NOT NULL,   -- who/what generated this: 'system','sensor','human','llm','safety'
    severity        TEXT    NOT NULL DEFAULT 'info',   -- debug/info/warn/error/critical
    superseded_by   INTEGER,            -- FK to events.id if this event is corrected
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    FOREIGN KEY (superseded_by) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_events_session   ON events(session_uuid);
CREATE INDEX IF NOT EXISTS idx_events_type      ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created   ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_severity  ON events(severity);

-- ─────────────────────────────────────────────
-- OBSERVATIONS
-- Sensor/body/world observations. Linked to events.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS observations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        INTEGER NOT NULL,
    sensor          TEXT    NOT NULL,   -- e.g. 'camera','microphone','imu','temperature'
    reading         TEXT    NOT NULL,   -- JSON: raw or processed value
    unit            TEXT,               -- e.g. 'celsius','lux','m/s2'
    confidence      REAL,               -- 0.0–1.0 if applicable
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- ─────────────────────────────────────────────
-- BODY STATE
-- Snapshot of BEAN's physical/resource state.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS body_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid    TEXT    NOT NULL,
    cpu_percent     REAL,
    ram_percent     REAL,
    gpu_percent     REAL,
    disk_percent    REAL,
    temperature_c   REAL,               -- primary SoC temp
    power_state     TEXT,               -- 'battery','wired','low','critical'
    motor_state     TEXT,               -- JSON: per-motor status if applicable
    uptime_seconds  REAL,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- REFLECTIONS
-- Generated after events. Grounded, not hallucinated.
-- A reflection must cite the event_ids it covers.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reflections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid    TEXT    NOT NULL,
    reflection_uuid TEXT    NOT NULL UNIQUE,
    trigger_type    TEXT    NOT NULL,   -- 'post_session','scheduled','event_threshold','manual'
    event_ids       TEXT    NOT NULL,   -- JSON array of event.id values covered
    event_count     INTEGER NOT NULL,
    summary         TEXT    NOT NULL,   -- what happened, grounded
    uncertainties   TEXT,               -- JSON array: things BEAN doesn't know
    questions       TEXT,               -- JSON array: curiosity items generated
    anomalies       TEXT,               -- JSON array: things that seemed unexpected
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- CURIOSITY
-- Questions BEAN generates. Tracked for resolution.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS curiosity (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reflection_id   INTEGER,            -- may be null if manually inserted
    question        TEXT    NOT NULL,
    context         TEXT,               -- what prompted it
    status          TEXT    NOT NULL DEFAULT 'open',  -- open/answered/deferred/withdrawn
    answer          TEXT,               -- filled in when resolved
    answered_at     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    FOREIGN KEY (reflection_id) REFERENCES reflections(id)
);

-- ─────────────────────────────────────────────
-- BOUNDARIES
-- Safety limits, consent rules, forbidden actions.
-- Versioned. Old rows kept for history.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS boundaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    boundary_uuid   TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    category        TEXT    NOT NULL,   -- 'safety','consent','autonomy','interaction'
    rule            TEXT    NOT NULL,   -- plain language statement of the rule
    enforcement     TEXT    NOT NULL,   -- 'hard_stop','warn_and_log','require_approval'
    added_by        TEXT    NOT NULL,   -- supervisor name or 'system'
    active          INTEGER NOT NULL DEFAULT 1,  -- 0 = superseded
    superseded_by   INTEGER,
    reason          TEXT,               -- why this boundary exists
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    FOREIGN KEY (superseded_by) REFERENCES boundaries(id)
);

-- ─────────────────────────────────────────────
-- CAPABILITIES
-- What BEAN can actually do. No wishful thinking.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS capabilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    description     TEXT    NOT NULL,
    status          TEXT    NOT NULL,   -- 'active','planned','disabled','experimental'
    layer           TEXT    NOT NULL,   -- 'hardware','sensor','memory','reasoning','autonomy'
    notes           TEXT,
    added_at        TEXT    NOT NULL DEFAULT (datetime('now','utc')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- RELATIONSHIPS / SUPERVISORS
-- Who is authorized to interact with BEAN and how.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS supervisors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    role            TEXT    NOT NULL,   -- 'primary','observer','teacher','emergency'
    permissions     TEXT    NOT NULL,   -- JSON array: what they can do
    added_by        TEXT    NOT NULL,
    active          INTEGER NOT NULL DEFAULT 1,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- DEVELOPMENTAL HISTORY
-- Major architecture changes. The changelog of BEAN's growth.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS developmental_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT    NOT NULL,
    change_summary  TEXT    NOT NULL,
    reason          TEXT    NOT NULL,
    changed_by      TEXT    NOT NULL,
    files_affected  TEXT,               -- JSON array
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

-- ─────────────────────────────────────────────
-- CONTINUITY SUMMARIES
-- Human-readable end-of-session or scheduled summaries.
-- Bridges the gap between raw events and narrative memory.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS continuity_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid    TEXT,               -- null = cross-session
    summary_type    TEXT    NOT NULL,   -- 'session_end','daily','milestone'
    content         TEXT    NOT NULL,   -- markdown narrative
    event_range_start INTEGER,          -- events.id range covered
    event_range_end   INTEGER,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);
