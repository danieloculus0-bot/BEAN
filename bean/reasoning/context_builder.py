"""Build compact, grounded context for BEAN reasoning providers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .proposal import init_reasoning_schema


def _conn(conn=None):
    if conn is not None:
        return conn
    from ..memory.store import get_store
    return get_store()._conn()


def build_reasoning_context(session_uuid: str, conn=None, event_limit: int = 25) -> dict[str, Any]:
    conn = _conn(conn)
    init_reasoning_schema(conn)
    context = {
        "session_uuid": session_uuid,
        "recent_events": _recent_events(conn, session_uuid, event_limit),
        "world_claims": _world_claims(conn),
        "pressure_signals": _empty_if_missing(conn, "inner_weather_reports"),
        "possibility_states": _empty_if_missing(conn, "cognition_possibility_states"),
        "speculative_summary": _speculative_summary(conn, session_uuid),
        "motion_enabled": False,
        "sentience_claimed": False,
    }
    persist_context_snapshot(conn, session_uuid, context)
    return context


def persist_context_snapshot(conn, session_uuid: str, context: dict[str, Any]) -> str:
    init_reasoning_schema(conn)
    snapshot_id = f"ctx_{uuid.uuid4().hex[:16]}"
    conn.execute(
        """
        INSERT INTO reasoning_context_snapshots (snapshot_id, session_uuid, context_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot_id, session_uuid, json.dumps(context), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return snapshot_id


def summarize_context(context: dict[str, Any]) -> str:
    return (
        f"events={len(context.get('recent_events', []))}; "
        f"world_claims={len(context.get('world_claims', []))}; "
        f"open_hypotheses={len(context.get('speculative_summary', {}).get('open_hypotheses', []))}; "
        f"motion_enabled={context.get('motion_enabled', False)}"
    )


def _recent_events(conn, session_uuid: str, limit: int) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(
            """
            SELECT id, event_type, subtype, summary, data, source, severity, created_at
            FROM events WHERE session_uuid=? ORDER BY id DESC LIMIT ?
            """,
            (session_uuid, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _world_claims(conn) -> list[dict[str, Any]]:
    try:
        rows = conn.execute("SELECT * FROM world_claims ORDER BY id DESC LIMIT 25").fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _empty_if_missing(conn, table: str) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 10").fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _speculative_summary(conn, session_uuid: str) -> dict[str, Any]:
    try:
        from ..speculation import init_speculation
        engine = init_speculation(conn)
        return engine.build_speculative_summary(session_uuid)
    except Exception:
        return {
            "open_hypotheses": [],
            "unresolved_speculative_claims": [],
            "contradicted_hypotheses": [],
            "recently_strengthened_hypotheses": [],
            "counts_by_status": {},
            "unresolved_count": 0,
        }
