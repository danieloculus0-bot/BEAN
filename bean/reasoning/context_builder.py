"""Bounded context packets for Brain 0.11.

This packet gives the reasoning provider a small, inspectable snapshot of BEAN's
records. It is a proposal context, not an execution context.
"""

from __future__ import annotations

import json
import uuid

from .schema import init_reasoning_schema

LIMITS = {
    "recent_events": 20,
    "active_boundaries": 20,
    "capabilities": 30,
    "active_world_claims": 20,
    "uncertainty_claims": 10,
    "wisdom_recent_traces": 10,
    "relationship_summaries": 10,
    "open_hypotheses": 10,
}


def _rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def _row(conn, sql: str, params: tuple = ()) -> dict:
    try:
        result = conn.execute(sql, params).fetchone()
        return dict(result) if result else {}
    except Exception:
        return {}


def _json_ids(rows: list[dict], key: str = "id") -> str:
    return json.dumps([row[key] for row in rows if key in row and row[key] is not None])


def _load_json(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except Exception:
        return fallback


def _identity(conn) -> dict:
    ident = _row(conn, "SELECT name, version, developmental_stage, hardware_body, what_bean_is, what_bean_is_not, updated_at FROM identity WHERE id=1")
    if ident:
        ident["hardware_body"] = _load_json(ident.get("hardware_body"), {})
    return ident


def _origin(conn) -> dict:
    return {
        "history": _row(conn, "SELECT version, change_summary, reason, changed_by, created_at FROM developmental_history WHERE version='BEAN_ORIGIN_COVENANT_001' ORDER BY id DESC LIMIT 1"),
        "summary": _row(conn, "SELECT summary_type, content, created_at FROM continuity_summaries WHERE summary_type='origin_covenant' ORDER BY id DESC LIMIT 1"),
    }


def _speculation(conn, session_uuid: str) -> dict:
    try:
        from ..speculation import init_speculation
        summary = init_speculation(conn).build_speculative_summary(session_uuid)
        summary["open_hypotheses"] = summary.get("open_hypotheses", [])[: LIMITS["open_hypotheses"]]
        return summary
    except Exception:
        return {"open_hypotheses": [], "counts_by_status": {}, "unresolved_count": 0}


def build_reasoning_context(session_uuid: str, source_event_id: int | None = None, packet_type: str = "manual", conn=None) -> dict:
    conn = init_reasoning_schema(conn)

    recent_events = _rows(conn, "SELECT id, event_type, subtype, summary, source, severity, created_at FROM events WHERE session_uuid=? ORDER BY id DESC LIMIT ?", (session_uuid, LIMITS["recent_events"]))
    boundaries = _rows(conn, "SELECT id, name, category, rule, enforcement, reason FROM boundaries WHERE active=1 ORDER BY category, name LIMIT ?", (LIMITS["active_boundaries"],))
    capabilities = _rows(conn, "SELECT id, name, description, status, layer, notes FROM capabilities ORDER BY layer, name LIMIT ?", (LIMITS["capabilities"],))
    active_claims = _rows(conn, "SELECT id, claim_id, key, content, category, source_type, confidence, evidence, notes FROM world_claims WHERE active=1 ORDER BY confidence DESC, id DESC LIMIT ?", (LIMITS["active_world_claims"],))
    uncertainty_claims = _rows(conn, "SELECT id, claim_id, key, content, category, source_type, confidence, evidence, notes FROM world_claims WHERE active=1 AND category='uncertainty' ORDER BY id DESC LIMIT ?", (LIMITS["uncertainty_claims"],))
    wisdom_traces = _rows(conn, "SELECT id, trace_id, source_event_id, root_trigger, pressure_delta_json, meaning_frame_id, uncertainty_score, created_at FROM wisdom_activation_traces ORDER BY id DESC LIMIT ?", (LIMITS["wisdom_recent_traces"],))
    relationships = _rows(conn, "SELECT id, relationship_id, supervisor_id, display_label, interaction_count, trust_score, trust_status, last_seen_at FROM supervisor_relationships WHERE active=1 ORDER BY last_seen_at DESC LIMIT ?", (LIMITS["relationship_summaries"],))

    context = {
        "identity_rules": {
            "llm_is_tool_not_identity": True,
            "use_evidence": True,
            "speculation_is_not_fact": True,
            "reasoning_proposals_do_not_act": True,
        },
        "limits": LIMITS,
        "session": {"session_uuid": session_uuid, "source_event_id": source_event_id, "packet_type": packet_type},
        "identity": _identity(conn),
        "origin_covenant": _origin(conn),
        "active_boundaries": boundaries,
        "capabilities": capabilities,
        "recent_events": recent_events,
        "active_world_claims": active_claims,
        "uncertainty_claims": uncertainty_claims,
        "wisdom_recent_traces": wisdom_traces,
        "relationship_summaries": relationships,
        "speculative_summary": _speculation(conn, session_uuid),
        "body_output_status": {"enabled": False},
    }

    packet_id = f"packet_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO reasoning_context_packets
            (packet_id, session_uuid, source_event_id, packet_type, context_json,
             included_event_ids_json, included_claim_ids_json, included_wisdom_trace_ids_json,
             included_relationship_ids_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            packet_id,
            session_uuid,
            source_event_id,
            packet_type,
            json.dumps(context),
            _json_ids(recent_events),
            _json_ids(active_claims + uncertainty_claims),
            _json_ids(wisdom_traces),
            _json_ids(relationships),
        ),
    )
    conn.commit()
    return {"packet_id": packet_id, "context": context}
