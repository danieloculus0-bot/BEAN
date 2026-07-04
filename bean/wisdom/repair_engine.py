"""Resolution records for Brain 0.9 wisdom."""

from __future__ import annotations

import json
import uuid

from .schema import init_wisdom_schema

RESOLUTION_TYPES = {"acknowledgement", "clarification", "reassurance", "behavior_change", "future_action", "boundary_reset", "evidence_update"}


def record_repair_attempt(session_uuid: str, repair_type: str, summary: str, pressure_before: dict, pressure_after: dict | None = None, source_event_id: int | None = None, evidence_refs: list | None = None, conn=None) -> dict:
    if repair_type not in RESOLUTION_TYPES:
        raise ValueError("invalid resolution type")
    c = init_wisdom_schema(conn)
    repair_id = f"repair_{uuid.uuid4().hex[:12]}"
    before_total = sum(float(v) for v in (pressure_before or {}).values())
    after_total = sum(float(v) for v in (pressure_after or {}).values()) if pressure_after is not None else before_total
    success = 1.0 if evidence_refs and pressure_after is not None and after_total < before_total else None
    c.execute(
        """
        INSERT INTO wisdom_repair_attempts
        (repair_id, session_uuid, source_event_id, repair_type, summary, action_taken_json,
         pressure_before_json, pressure_after_json, repair_success, evidence_refs_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (repair_id, session_uuid, source_event_id, repair_type, summary, json.dumps({"type": repair_type}), json.dumps(pressure_before or {}), json.dumps(pressure_after) if pressure_after is not None else None, success, json.dumps(evidence_refs or [])),
    )
    c.commit()
    return {"repair_id": repair_id, "repair_success": success}
