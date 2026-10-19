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
import math
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .store import get_store
from .audit_mirror import reconcile_event_mirror, AuditMirrorError


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



# Preserve unknown numeric measurements without silently turning them into
# null, ordinary numbers, or non-standard JSON tokens. This is a representation
# contract, not a rule about what BEAN may think or investigate.
_NONFINITE_LABELS = {
    "NaN": "nan", "Infinity": "+inf", "-Infinity": "-inf",
}


def _json_compatible_observation(value):
    """Make a JSON-portable copy of sensor/event data, preserving nonfinite tags.

    Existing ordinary JSON values are left unchanged. No imputation or
    inference is performed: the consumer decides how to treat an uncertain
    numerical measurement.
    """
    if isinstance(value, float):
        if math.isnan(value):
            return {"$bean_nonfinite_float": "nan"}
        if math.isinf(value):
            return {"$bean_nonfinite_float": "+inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, dict):
        return {key: _json_compatible_observation(item)
                for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_compatible_observation(item) for item in value]
    return value


def parse_event_data(text: str):
    """Read both compliant event JSON and legacy Python NaN/Infinity tokens.

    Legacy values are translated into explicit structured observations without
    modifying historical SQLite rows or their verified JSONL mirror bytes.
    """
    return json.loads(
        text,
        parse_constant=lambda token: {
            "$bean_nonfinite_float": _NONFINITE_LABELS[token]
        },
    )


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
    data_json = (json.dumps(_json_compatible_observation(data), allow_nan=False)
                 if data is not None else None)

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

    # SQLite was committed first. If mirror I/O fails, raise an explicit
    # error with the committed ID so no caller retries the event blindly.
    # Next init_store/boot replays missing events from authoritative SQLite.
    try:
        reconcile_event_mirror(store)
    except AuditMirrorError as exc:
        raise AuditMirrorError(
            f"Committed BEAN event id={cursor.lastrowid} uuid={event_uuid}, "
            f"but JSONL mirror is unhealthy: {exc}"
        ) from exc
    return cursor.lastrowid


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
