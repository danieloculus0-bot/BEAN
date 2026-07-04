"""Brain 0.9 wisdom maintenance."""

from __future__ import annotations

from .loop_detector import list_loop_signatures
from .schema import init_wisdom_schema


def run_wisdom_maintenance(session_uuid: str, conn=None) -> dict:
    c = init_wisdom_schema(conn)
    counts = {}
    for table in ["wisdom_activation_traces", "wisdom_meaning_frames", "wisdom_repair_attempts", "wisdom_loop_signatures", "wisdom_wound_patterns"]:
        try:
            row = c.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
            counts[table] = int(row["n"] if row else 0)
        except Exception:
            counts[table] = 0
    return {"session_uuid": session_uuid, "counts": counts, "active_loops": list_loop_signatures(conn=c)}
