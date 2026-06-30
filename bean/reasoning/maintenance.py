"""Maintenance helpers for reasoning proposals."""

from __future__ import annotations

from datetime import datetime, timezone

from .proposal import init_reasoning_schema


def run_reasoning_maintenance(conn=None, dry_run: bool = False, stale_hours: int = 72) -> dict:
    if conn is None:
        from ..memory.store import get_store
        conn = get_store()._conn()
    init_reasoning_schema(conn)
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "dry_run": bool(dry_run), "stale_expired": 0}
    rows = conn.execute(
        f"""
        SELECT proposal_id FROM reasoning_proposals
        WHERE status='pending' AND created_at < datetime('now', '-{int(stale_hours)} hours')
        """
    ).fetchall()
    report["stale_expired"] = len(rows)
    if not dry_run:
        for row in rows:
            conn.execute("UPDATE reasoning_proposals SET status='expired' WHERE proposal_id=?", (row["proposal_id"],))
        conn.commit()
    return report
