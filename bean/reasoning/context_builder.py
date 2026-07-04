"""Context packets for Brain 0.11."""

import json
import uuid
from .schema import init_reasoning_schema


def build_reasoning_context(session_uuid: str, source_event_id: int | None = None, packet_type: str = "manual", conn=None) -> dict:
    conn = init_reasoning_schema(conn)
    context = {"session": {"session_uuid": session_uuid}, "identity_rules": {"llm_is_tool_not_identity": True, "use_evidence": True}, "recent_events": [], "motion_status": {"motion_enabled": False}}
    try:
        context["recent_events"] = [dict(r) for r in conn.execute("SELECT id, event_type, summary FROM events WHERE session_uuid=? ORDER BY id DESC LIMIT 20", (session_uuid,)).fetchall()]
    except Exception:
        pass
    try:
        from ..speculation import init_speculation
        context["speculative_summary"] = init_speculation(conn).build_speculative_summary(session_uuid)
    except Exception:
        context["speculative_summary"] = {"open_hypotheses": [], "counts_by_status": {}}
    packet_id = f"packet_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO reasoning_context_packets (packet_id, session_uuid, source_event_id, packet_type, context_json) VALUES (?, ?, ?, ?, ?)", (packet_id, session_uuid, source_event_id, packet_type, json.dumps(context)))
    conn.commit()
    return {"packet_id": packet_id, "context": context}
