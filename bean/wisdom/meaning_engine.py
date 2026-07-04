"""Meaning-frame construction for Brain 0.9 wisdom."""

from __future__ import annotations

import json
import uuid

from .schema import init_wisdom_schema


def build_meaning_frame(event_summary: str, triggers: list, pressure_delta: dict, stated_reason: str | None = None) -> dict:
    trigger_names = [getattr(t, "trigger_type", None) or t.get("trigger_type") for t in triggers]
    symbolic = "possible event significance"
    assumption = "meaning remains unresolved"
    if "future_plan_disruption" in trigger_names:
        symbolic = "possible future-plan disruption"
        assumption = "the plan may need support or revision"
    evidence_against = []
    if stated_reason:
        evidence_against.append(f"stated reason: {stated_reason}")
    return {
        "event_fact": event_summary,
        "symbolic_interpretation": symbolic,
        "assumption_candidate": assumption,
        "evidence_for": [event_summary] if event_summary else [],
        "evidence_against": evidence_against,
        "alternative_interpretations": ["capacity factor", "timing factor", "communication factor"],
        "uncertainty_score": max(0.1, min(1.0, pressure_delta.get("uncertainty_load", 0.5) or 0.5)),
        "status": "open",
    }


def persist_meaning_frame(session_uuid: str, source_event_id: int | None, frame: dict, conn=None) -> str:
    c = init_wisdom_schema(conn)
    frame_id = f"frame_{uuid.uuid4().hex[:12]}"
    c.execute(
        """
        INSERT INTO wisdom_meaning_frames
        (frame_id, session_uuid, source_event_id, event_fact, symbolic_interpretation,
         assumption_candidate, evidence_for_json, evidence_against_json,
         alternative_interpretations_json, uncertainty_score, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            frame_id, session_uuid, source_event_id, frame["event_fact"],
            frame.get("symbolic_interpretation"), frame.get("assumption_candidate"),
            json.dumps(frame.get("evidence_for", [])), json.dumps(frame.get("evidence_against", [])),
            json.dumps(frame.get("alternative_interpretations", [])),
            float(frame.get("uncertainty_score", 0.5)), frame.get("status", "open"),
        ),
    )
    c.commit()
    return frame_id
