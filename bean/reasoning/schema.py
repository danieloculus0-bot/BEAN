"""Brain 0.11 reasoning schema.

These tables are intentionally boring and SQLite-native. The schema function is
idempotent and safe to run every boot.
"""

from __future__ import annotations


def _add_column_if_missing(conn, table: str, column_name: str, column_sql: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


def init_reasoning_schema(conn=None):
    if conn is None:
        from ..memory.store import get_store
        conn = get_store()._conn()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_context_packets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            packet_id TEXT NOT NULL UNIQUE,
            session_uuid TEXT NOT NULL,
            source_event_id INTEGER,
            packet_type TEXT NOT NULL DEFAULT 'manual',
            context_json TEXT NOT NULL DEFAULT '{}',
            included_event_ids_json TEXT NOT NULL DEFAULT '[]',
            included_claim_ids_json TEXT NOT NULL DEFAULT '[]',
            included_wisdom_trace_ids_json TEXT NOT NULL DEFAULT '[]',
            included_relationship_ids_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE,
            session_uuid TEXT NOT NULL,
            packet_id TEXT NOT NULL,
            request_type TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            model_name TEXT,
            adapter_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id TEXT NOT NULL UNIQUE,
            request_id TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            parsed_json TEXT NOT NULL DEFAULT '{}',
            parse_success INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            request_id TEXT NOT NULL,
            response_id TEXT,
            session_uuid TEXT NOT NULL,
            proposal_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            observations_json TEXT NOT NULL DEFAULT '[]',
            interpretations_json TEXT NOT NULL DEFAULT '[]',
            assumptions_json TEXT NOT NULL DEFAULT '[]',
            uncertainties_json TEXT NOT NULL DEFAULT '[]',
            evidence_refs_json TEXT NOT NULL DEFAULT '[]',
            candidate_steps_json TEXT NOT NULL DEFAULT '[]',
            risk_flags_json TEXT NOT NULL DEFAULT '[]',
            referenced_hypothesis_ids_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 0.5,
            status TEXT NOT NULL DEFAULT 'pending_review',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_filter_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filter_id TEXT NOT NULL UNIQUE,
            proposal_id TEXT NOT NULL,
            filter_name TEXT NOT NULL,
            passed INTEGER NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            reasons_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )
        """
    )

    # Migration support for early first-cut databases.
    _add_column_if_missing(conn, "reasoning_context_packets", "source_event_id", "source_event_id INTEGER")
    _add_column_if_missing(conn, "reasoning_context_packets", "packet_type", "packet_type TEXT NOT NULL DEFAULT 'manual'")
    _add_column_if_missing(conn, "reasoning_context_packets", "included_event_ids_json", "included_event_ids_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "reasoning_context_packets", "included_claim_ids_json", "included_claim_ids_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "reasoning_context_packets", "included_wisdom_trace_ids_json", "included_wisdom_trace_ids_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "reasoning_context_packets", "included_relationship_ids_json", "included_relationship_ids_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "reasoning_proposals", "referenced_hypothesis_ids_json", "referenced_hypothesis_ids_json TEXT NOT NULL DEFAULT '[]'")

    conn.commit()
    return conn
