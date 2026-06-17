"""
bean/reflection/reflect.py

The reflection pass. Reads real events. Writes grounded reflections.
No hallucination. No "BEAN felt curious about the universe."
Only what the event log actually contains.

A reflection must:
- Cite the event IDs it covers.
- State only what the events show.
- Note genuine uncertainties (not performed ones).
- Generate questions only when the events actually raise them.
- Flag anomalies that are statistically or logically unexpected.

This is not a feelings module. It is a pattern-recognition and
summarization pass over the actual event record.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..memory.store import get_store
from ..memory.event_logger import log_event, EventType, Source, Severity


def run_reflection(
    session_uuid: str,
    trigger_type: str = "post_session",
    event_ids: Optional[list] = None,
) -> dict:
    """
    Run a reflection pass over a set of events.

    If event_ids is None, reflects over all events in the session.
    Returns the reflection record as a dict.

    trigger_type: post_session / scheduled / event_threshold / manual
    """
    store = get_store()

    if event_ids:
        placeholders = ",".join("?" * len(event_ids))
        rows = store.fetchall(
            f"""
            SELECT id, event_type, subtype, summary, source, severity, data, created_at
            FROM events
            WHERE id IN ({placeholders})
            ORDER BY id ASC
            """,
            tuple(event_ids),
        )
    else:
        rows = store.fetchall(
            """
            SELECT id, event_type, subtype, summary, source, severity, data, created_at
            FROM events
            WHERE session_uuid = ?
            ORDER BY id ASC
            """,
            (session_uuid,),
        )

    events = [dict(r) for r in rows]
    if not events:
        return {"status": "no_events", "reflection_uuid": None}

    covered_ids = [e["id"] for e in events]

    summary = _build_summary(events)
    uncertainties = _identify_uncertainties(events)
    questions = _generate_questions(events, session_uuid)
    anomalies = _detect_anomalies(events)

    reflection_uuid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    cursor = store.execute(
        """
        INSERT INTO reflections
            (session_uuid, reflection_uuid, trigger_type, event_ids,
             event_count, summary, uncertainties, questions, anomalies, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_uuid,
            reflection_uuid,
            trigger_type,
            json.dumps(covered_ids),
            len(covered_ids),
            summary,
            json.dumps(uncertainties) if uncertainties else None,
            json.dumps(questions) if questions else None,
            json.dumps(anomalies) if anomalies else None,
            now,
        ),
    )
    reflection_id = cursor.lastrowid
    store.commit()

    for q in questions:
        store.execute(
            """
            INSERT INTO curiosity (reflection_id, question, context, status, created_at)
            VALUES (?, ?, ?, 'open', ?)
            """,
            (reflection_id, q["question"], q.get("context"), now),
        )
    store.commit()

    log_event(
        session_uuid=session_uuid,
        event_type=EventType.REFLECTION,
        summary=(
            f"Reflection completed. {len(covered_ids)} events reviewed. "
            f"{len(questions)} questions generated. "
            f"{len(anomalies)} anomalies noted."
        ),
        source=Source.SYSTEM,
        data={
            "reflection_uuid": reflection_uuid,
            "event_count": len(covered_ids),
            "question_count": len(questions),
            "anomaly_count": len(anomalies),
        },
    )

    return {
        "status": "ok",
        "reflection_uuid": reflection_uuid,
        "reflection_id": reflection_id,
        "event_count": len(covered_ids),
        "summary": summary,
        "uncertainties": uncertainties,
        "questions": questions,
        "anomalies": anomalies,
    }


def _build_summary(events: list) -> str:
    if not events:
        return "No events to summarize."

    type_counts = {}
    for e in events:
        t = e["event_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    first_ts = events[0]["created_at"]
    last_ts = events[-1]["created_at"]
    total = len(events)

    lines = [
        f"Reflection covers {total} event(s) from {first_ts} to {last_ts}.",
        "Event type breakdown:",
    ]
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {etype}: {count}")

    errors = [e for e in events if e["severity"] in ("error", "critical")]
    warnings = [e for e in events if e["severity"] == "warn"]
    if errors:
        lines.append(f"Errors/critical events ({len(errors)}):")
        for e in errors:
            lines.append(f"  [{e['severity'].upper()}] {e['summary']}")
    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        for e in warnings[:5]:
            lines.append(f"  [WARN] {e['summary']}")

    return "\n".join(lines)


def _identify_uncertainties(events: list) -> list:
    uncertainties = []

    sensor_events = [e for e in events if e["event_type"] == "sensor_reading"]
    for e in sensor_events:
        if not e.get("data"):
            uncertainties.append(
                f"Sensor reading event {e['id']} has no data payload. "
                "Reading may be unreliable."
            )

    error_ids = {e["id"] for e in events if e["severity"] in ("error", "critical")}
    if error_ids:
        uncertainties.append(
            f"{len(error_ids)} error/critical event(s) occurred. "
            "Whether these were resolved is not confirmed in the event record."
        )

    store = get_store()
    bad_shutdowns = store.fetchall(
        """
        SELECT session_uuid, shutdown_reason FROM sessions
        WHERE shutdown_reason NOT IN ('clean')
        AND shutdown_reason IS NOT NULL
        ORDER BY boot_count DESC LIMIT 3
        """
    )
    for row in bad_shutdowns:
        uncertainties.append(
            f"Previous session {row['session_uuid'][:8]} ended with "
            f"reason '{row['shutdown_reason']}'. State at that point is uncertain."
        )

    return uncertainties


def _generate_questions(events: list, session_uuid: str) -> list:
    questions = []
    event_types = {e["event_type"] for e in events}

    error_events = [e for e in events if e["severity"] in ("error", "critical")]
    for e in error_events:
        questions.append({
            "question": f"What caused: '{e['summary']}'? Is it recurring?",
            "context": f"Error at {e['created_at']}, event id {e['id']}.",
        })

    if "sensor_reading" not in event_types and len(events) > 3:
        questions.append({
            "question": "No sensor readings in this session. Are sensors connected and functional?",
            "context": "Session had multiple events but zero sensor_reading events.",
        })

    store = get_store()
    session_row = store.fetchone(
        "SELECT boot_count FROM sessions WHERE session_uuid = ?",
        (session_uuid,),
    )
    if session_row and session_row["boot_count"] > 1:
        prev = store.fetchone(
            "SELECT shutdown_reason FROM sessions WHERE boot_count = ?",
            (session_row["boot_count"] - 1,),
        )
        if prev and prev["shutdown_reason"] not in ("clean", None):
            questions.append({
                "question": "Previous session did not end cleanly. Was anything lost or corrupted?",
                "context": f"Previous session shutdown_reason: {prev['shutdown_reason']}",
            })

    return questions


def _detect_anomalies(events: list) -> list:
    anomalies = []

    boot_count = sum(1 for e in events if e["event_type"] == "boot")
    if boot_count > 1:
        anomalies.append(
            f"Multiple boot events ({boot_count}) in a single session. "
            "Should not happen under normal conditions."
        )

    safety_events = [e for e in events if e["event_type"] == "safety_trigger"]
    if safety_events:
        anomalies.append(f"{len(safety_events)} safety trigger event(s) in this session.")

    bv_events = [e for e in events if e["event_type"] == "boundary_violation_attempt"]
    if bv_events:
        anomalies.append(
            f"{len(bv_events)} boundary violation attempt(s). Supervisor review recommended."
        )

    if len(events) > 200:
        anomalies.append(
            f"Unusually high event count ({len(events)}) for one reflection window. "
            "Check for runaway logging loops."
        )

    return anomalies


def get_reflections(session_uuid: str) -> list:
    store = get_store()
    rows = store.fetchall(
        "SELECT * FROM reflections WHERE session_uuid = ? ORDER BY id DESC",
        (session_uuid,),
    )
    return [dict(r) for r in rows]


def get_open_questions() -> list:
    store = get_store()
    rows = store.fetchall(
        "SELECT * FROM curiosity WHERE status = 'open' ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]
