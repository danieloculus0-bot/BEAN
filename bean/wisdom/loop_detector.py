"""Loop-signature tracking for Brain 0.9 wisdom."""

from __future__ import annotations

import json
import uuid

from .schema import init_wisdom_schema


def update_loop_signature(name: str, trigger_signature: dict, role_a_pattern: str = "", role_b_pattern: str = "", escalation_pattern: str = "", repair_pattern: str = "", conn=None) -> dict:
    c = init_wisdom_schema(conn)
    row = c.execute("SELECT * FROM wisdom_loop_signatures WHERE name=? AND active=1", (name,)).fetchone()
    if row:
        c.execute("UPDATE wisdom_loop_signatures SET recurrence_count=recurrence_count+1, last_seen_at=datetime('now','utc'), updated_at=datetime('now','utc') WHERE id=?", (row["id"],))
        loop_id = row["loop_id"]
    else:
        loop_id = f"loop_{uuid.uuid4().hex[:12]}"
        c.execute(
            """
            INSERT INTO wisdom_loop_signatures
            (loop_id, name, trigger_signature_json, role_a_pattern, role_b_pattern, escalation_pattern, repair_pattern, recurrence_count, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now','utc'))
            """,
            (loop_id, name, json.dumps(trigger_signature or {}), role_a_pattern, role_b_pattern, escalation_pattern, repair_pattern),
        )
    c.commit()
    return {"loop_id": loop_id, "name": name}


def list_loop_signatures(limit: int = 20, conn=None) -> list[dict]:
    c = init_wisdom_schema(conn)
    rows = c.execute("SELECT * FROM wisdom_loop_signatures WHERE active=1 ORDER BY recurrence_count DESC, id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
