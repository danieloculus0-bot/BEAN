"""
bean/memory/event_logger.py

Append-only event logger. This is the spine.
Nothing is deleted. Nothing is faked.
Every event that changes BEAN's state, context, or understanding
should come through here.

EventType is the canonical vocabulary. If you want a new event type,
add it here and document it. Don't invent strings in calling code.
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .store import get_store


class EventType(str, Enum):
    # Lifecycle
    BOOT            = "boot"
    SHUTDOWN        = "shutdown"
    SESSION_START   = "session_start"
    SESSION_END     = "session_end"

    # Interaction
    HUMAN_INPUT     = "human_input"
    HUMAN_COMMAND   = "human_command"
    LLM_RESPONSE    = "llm_response"
    SUPERVISOR_NOTE = "supervisor_note"

    # Sensing
    SENSOR_READING  = "sensor_reading"
    BODY_STATE      = "body_state"
    OBSERVATION     = "observation"

    # Cognition
    REFLECTION      = "reflection"
    CURIOSITY       = "curiosity"
    WORLD_MODEL_UPDATE = "world_model_update"
    SELF_MODEL_UPDATE  = "self_model_update"

    # Learning
    FACT_LEARNED    = "fact_learned"
    PREFERENCE_UPDATE = "preference_update"
    BOUNDARY_DECISION = "boundary_decision"

    # System
    ERROR           = "error"
    WARNING         = "warning"
    CONFIG_CHANGE   = "config_change"
    CAPABILITY_CHANGE = "capability_change"
    CODE_CHANGE     = "code_change"
    MEMORY_CONSOLIDATION = "memory_consolidation"

    # Safety
    SAFETY_TRIGGER  = "safety_trigger"
    OVERRIDE        = "override"
    BOUNDARY_VIOLATION_ATTEMPT = "boundary_violation_attempt"


class Severity(str, Enum):
    DEBUG    = "debug"
    INFO     = "info"
    WARN     = "warn"
    ERROR    = "error"
    CRITICAL = "critical"


class Source(str, Enum):
    SYSTEM   = "system"
    SENSOR   = "sensor"
    HUMAN    = "human"
    LLM      = "llm"
    SAFETY   = "safety"
    TIMER    = "timer"


def log_event(
    session_uuid: str,
    event_type: EventType,
    summary: str,
    source: Source = Source.SYSTEM,
    subtype: Optional[str] = None,
    data: Optional[dict] = None,
    severity: Severity = Severity.INFO,
) -> int:
    """
    Write one event to the events table.
    Returns the new row's id.
    
    This is the only correct way to record that something happened.
    Do not write to the events table directly anywhere else.
    """
    store = get_store()
    event_uuid = str(uuid.uuid4())
    data_json = json.dumps(data) if data is not None else None

    cursor = store.execute(
        """
        INSERT INTO events
            (session_uuid, event_uuid, event_type, subtype, summary,
             data, source, severity, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_uuid,
            event_uuid,
            event_type.value,
            subtype,
            summary,
            data_json,
            source.value,
            severity.value,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    store.commit()

    # Also append to JSONL audit log
    _append_jsonl(
        session_uuid=session_uuid,
        event_id=cursor.lastrowid,
        event_uuid=event_uuid,
        event_type=event_type.value,
        subtype=subtype,
        summary=summary,
        source=source.value,
        severity=severity.value,
        data=data,
    )

    return cursor.lastrowid


def _append_jsonl(session_uuid, event_id, event_uuid, event_type,
                   subtype, summary, source, severity, data):
    """
    Append to the JSONL audit log. Belt-and-suspenders.
    The JSONL log is not the truth — the SQLite DB is.
    But the JSONL is an independent human-readable audit trail.
    """
    import os
    from pathlib import Path

    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "events.jsonl"

    record = {
        "id": event_id,
        "session_uuid": session_uuid,
        "event_uuid": event_uuid,
        "event_type": event_type,
        "subtype": subtype,
        "summary": summary,
        "source": source,
        "severity": severity,
        "data": data,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def get_recent_events(session_uuid: str, limit: int = 50) -> list[dict]:
    """Return the N most recent events for a session, newest first."""
    store = get_store()
    rows = store.fetchall(
        """
        SELECT id, event_uuid, event_type, subtype, summary,
               data, source, severity, created_at
        FROM events
        WHERE session_uuid = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_uuid, limit),
    )
    return [dict(r) for r in rows]


def get_events_by_type(event_type: EventType, limit: int = 100) -> list[dict]:
    """Retrieve events of a specific type across all sessions."""
    store = get_store()
    rows = store.fetchall(
        """
        SELECT id, session_uuid, event_uuid, event_type, subtype,
               summary, data, source, severity, created_at
        FROM events
        WHERE event_type = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (event_type.value, limit),
    )
    return [dict(r) for r in rows]


def supersede_event(event_id: int, replacement_id: int):
    """
    Mark an event as superseded by a later correction.
    The original row is never deleted — only annotated.
    """
    store = get_store()
    store.execute(
        "UPDATE events SET superseded_by = ? WHERE id = ?",
        (replacement_id, event_id),
    )
    store.commit()
