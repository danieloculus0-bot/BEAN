"""Brain 0.9 wisdom trigger engine.

This is a deterministic local layer for reminders and meaning frames. It does
not ask an LLM, does not execute actions, and does not claim feeling.
"""

from __future__ import annotations

from typing import Any

from .schema import init_wisdom_schema, record_activation_trace, record_meaning_frame, seed_default_triggers


def evaluate_text_for_wisdom(conn, session_uuid: str, text: str, source: str = "system") -> dict[str, Any]:
    conn = conn
    init_wisdom_schema(conn)
    seed_default_triggers(conn)
    lowered = (text or "").lower()
    rows = conn.execute("SELECT * FROM wisdom_triggers WHERE active=1 ORDER BY id").fetchall()
    activations: list[dict[str, Any]] = []
    for row in rows:
        if str(row["pattern"]).lower() in lowered:
            trace_id = record_activation_trace(
                conn,
                session_uuid=session_uuid,
                trigger_id=row["trigger_id"],
                category=row["category"],
                input_text=text,
                reminder=row["reminder"],
                source=source,
            )
            activations.append({
                "trace_id": trace_id,
                "trigger_id": row["trigger_id"],
                "name": row["name"],
                "category": row["category"],
                "severity": row["severity"],
                "reminder": row["reminder"],
            })
    frame_id = None
    if activations:
        frame_id = record_meaning_frame(
            conn,
            session_uuid=session_uuid,
            title="Wisdom trigger review",
            summary="One or more local wisdom triggers fired. Treat reminders as discipline, not emotion.",
            evidence=[{"trace_id": item["trace_id"], "name": item["name"]} for item in activations],
            uncertainty=[],
            source=source,
        )
    return {
        "activated": bool(activations),
        "activation_count": len(activations),
        "activations": activations,
        "meaning_frame_id": frame_id,
        "motion_enabled": False,
        "sentience_claimed": False,
    }
