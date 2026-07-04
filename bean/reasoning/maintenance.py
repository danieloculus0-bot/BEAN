"""Brain 0.11 maintenance."""

from .schema import init_reasoning_schema


def run_reasoning_maintenance(session_uuid: str, conn=None) -> dict:
    conn = init_reasoning_schema(conn)
    tables = ["reasoning_context_packets", "reasoning_requests", "reasoning_responses", "reasoning_proposals", "reasoning_filter_results"]
    counts = {}
    for table in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
            counts[table] = int(row["n"] if row else 0)
        except Exception:
            counts[table] = 0
    return {"session_uuid": session_uuid, "counts": counts}
