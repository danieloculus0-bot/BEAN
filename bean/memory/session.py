"""
bean/memory/session.py

Session management. BEAN's continuity lives here.
Each boot creates a session. Sessions are never deleted.
Boot count is monotonically increasing and stored in the DB.
If BEAN reboots 500 times, it has 500 session rows.
That IS the continuity record.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from .store import get_store
from .event_logger import log_event, EventType, Severity, Source


def begin_session() -> str:
    """
    Start a new session. Called once at boot.
    Returns the session_uuid for this run.
    """
    store = get_store()

    # Get current boot count
    row = store.fetchone("SELECT MAX(boot_count) as max_boot FROM sessions")
    boot_count = (row["max_boot"] or 0) + 1

    session_uuid = str(uuid.uuid4())
    boot_time = datetime.now(timezone.utc).isoformat()

    store.execute(
        """
        INSERT INTO sessions (session_uuid, boot_time, boot_count)
        VALUES (?, ?, ?)
        """,
        (session_uuid, boot_time, boot_count),
    )
    store.commit()

    log_event(
        session_uuid=session_uuid,
        event_type=EventType.BOOT,
        summary=f"BEAN booted. Session {session_uuid[:8]}. Boot #{boot_count}.",
        source=Source.SYSTEM,
        data={"boot_count": boot_count, "session_uuid": session_uuid},
    )

    return session_uuid


def end_session(session_uuid: str, reason: str = "clean", notes: Optional[str] = None):
    """
    Close the current session. Called at shutdown.
    reason: clean / error / power_loss / supervisor / keyboard_interrupt
    """
    store = get_store()
    shutdown_time = datetime.now(timezone.utc).isoformat()

    log_event(
        session_uuid=session_uuid,
        event_type=EventType.SHUTDOWN,
        summary=f"BEAN shutting down. Reason: {reason}.",
        source=Source.SYSTEM,
        data={"reason": reason, "notes": notes},
        severity=Severity.INFO if reason == "clean" else Severity.WARN,
    )

    store.execute(
        """
        UPDATE sessions
        SET shutdown_time = ?, shutdown_reason = ?, notes = ?
        WHERE session_uuid = ?
        """,
        (shutdown_time, reason, notes, session_uuid),
    )
    store.commit()


def get_session(session_uuid: str) -> Optional[dict]:
    store = get_store()
    row = store.fetchone(
        "SELECT * FROM sessions WHERE session_uuid = ?", (session_uuid,)
    )
    return dict(row) if row else None


def get_continuity_context(limit: int = 5) -> dict:
    """
    Return a structured continuity context: recent sessions + boot count.
    This is what BEAN reads at startup to know where it is in its history.
    """
    store = get_store()

    recent = store.fetchall(
        """
        SELECT session_uuid, boot_time, shutdown_time, shutdown_reason,
               boot_count, notes
        FROM sessions
        ORDER BY boot_count DESC
        LIMIT ?
        """,
        (limit,),
    )

    total_boots = store.fetchone("SELECT COUNT(*) as n FROM sessions")["n"]
    total_events = store.fetchone("SELECT COUNT(*) as n FROM events")["n"]

    return {
        "total_boots": total_boots,
        "total_events": total_events,
        "recent_sessions": [dict(r) for r in recent],
    }
