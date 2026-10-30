"""Opt-in, SINGLE-USER local MCP memory using actual BEAN Core SQLite events.

This module invokes BeanReasoningLayer and its canonical, mirrored event log;
it is NOT browser-localStorage, a published service, or independently verified
knowledge. Deliberately no shared/public sessions and no automatic recording.
Only enable over trusted loopback + an explicitly configured MCP connection.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from typing import Iterator

from bean.integration import BeanReasoningLayer
from bean.integration.public_plugin import _LOCK as _CORE_LOCK
from bean.memory.event_logger import EventType, Source

SUBTYPE = "local_mcp_memory_v1"
MAX_ACTIVE = 40
MAX_TOPIC = 90
MAX_NOTE = 700
ACTIVE_HOURS = 48
STOP_WORDS = frozenset({
    "the", "and", "what", "where", "which", "who", "when", "why", "how",
    "are", "was", "were", "is", "do", "does", "did", "you", "your",
    "my", "our", "for", "about", "remember", "from", "tell", "me",
    "it", "this", "that", "can", "with", "of", "to", "a", "an",
})
TOKEN = re.compile(r"[a-z0-9]+")


def _validate(value: str, field: str, limit: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f"{field} needs 1..{limit} characters")
    if "\x00" in value or any(ord(c) < 32 and c not in "\n\t\r" for c in value):
        raise ValueError(f"{field} contains invalid controls")
    return value.strip()


def _path(database: str | Path | None) -> Path:
    location = database if database is not None else os.environ.get("BEAN_LOCAL_MEMORY_DB")
    if not location:
        raise RuntimeError("Configure BEAN_LOCAL_MEMORY_DB explicitly; never infer a public database")
    db = Path(location).expanduser()
    if not db.is_absolute():
        raise ValueError("BEAN_LOCAL_MEMORY_DB must be an absolute local path")
    if db.suffix not in (".sqlite", ".sqlite3", ".db"):
        raise ValueError("Use a local SQLite database filename")
    return db


@contextmanager
def _layer(database: str | Path | None) -> Iterator[BeanReasoningLayer]:
    # The actual Core singleton must NOT be concurrently switched by another
    # MCP tool. Reuse public_plugin's shared lock for process-wide isolation.
    with _CORE_LOCK:
        with BeanReasoningLayer(str(_path(database))) as layer:
            yield layer


def _records(layer: BeanReasoningLayer) -> list[dict]:
    rows = layer.store.fetchall(
        "SELECT id,session_uuid,source,created_at,data FROM events "
        "WHERE subtype=? AND event_type=? ORDER BY id ASC",
        (SUBTYPE, EventType.OBSERVATION.value),
    )
    result = []
    for row in rows:
        data = json.loads(row["data"])
        if data.get("status") != "caller_supplied_unverified" or not all(
            isinstance(data.get(k), str) for k in ("topic", "note")
        ):
            raise ValueError("Unexpected BEAN local memory event; refusing to reinterpret")
        result.append({
            "id": row["id"], "session": row["session_uuid"],
            "topic": data["topic"], "note": data["note"],
            "provenance": "caller_supplied_unverified", "created_at": row["created_at"],
        })
    return result


def _current(records: list[dict], now: datetime) -> list[dict]:
    cutoff = now - timedelta(hours=ACTIVE_HOURS)
    return [r for r in records if datetime.fromisoformat(r["created_at"]) >= cutoff]


def remember(topic: str, note: str, *, database: str | Path | None = None) -> dict:
    """Store explicitly user-requested memory in BEAN's real mirrored ledger."""
    topic = _validate(topic, "topic", MAX_TOPIC)
    note = _validate(note, "note", MAX_NOTE)
    with _layer(database) as layer:
        active = _current(_records(layer), datetime.now(timezone.utc))
        if len(active) >= MAX_ACTIVE:
            raise ValueError("Short-run memory at capacity. No note was saved.")
        event_id = layer.record_event(
            "Unverified local MCP memory: " + topic,
            event_type=EventType.OBSERVATION, source=Source.SYSTEM,
            subtype=SUBTYPE,
            data={"topic": topic, "note": note, "status": "caller_supplied_unverified"},
        )
        return {
            "saved": True, "event_id": event_id, "topic": topic,
            "provenance": "caller_supplied_unverified",
            "persistence": "real_bean_core_sqlite_and_jsonl_mirror",
            "model_training": False, "verified_fact": False,
            "scope": "single_local_BEAN_instance",
        }


def _words(value: str) -> set[str]:
    return {word for word in TOKEN.findall(value.lower())
            if len(word) > 1 and word not in STOP_WORDS}


def recall(query: str, *, database: str | Path | None = None, limit: int = 10) -> dict:
    """Return short-run notes or an explicit no-match result; never write replies."""
    query = _validate(query, "query", 200)
    if not type(limit) is int or not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    with _layer(database) as layer:
        records = _current(_records(layer), datetime.now(timezone.utc))
    words = _words(query)
    scored = []
    for record in records:
        strength = 3 * len(words & _words(record["topic"])) + len(words & _words(record["note"]))
        if strength > 0:
            scored.append((strength, record["id"], record))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    matches = [item[2] for item in scored[:limit]]
    # No ranking based on factual confidence: source is unverified.
    groups = {}
    for record in matches:
        groups.setdefault(record["topic"].casefold(), set()).add(record["note"])
    return {
        "query": query, "matches": matches, "count": len(matches),
        "no_matching_memory": not bool(matches),
        "conflicting_notes": any(len(values) > 1 for values in groups.values()),
        "fact_verification": "not_performed",
        "memory_window_hours": ACTIVE_HOURS,
        "response_policy": "Quote attributed notes or abstain; do not fabricate a missing memory.",
    }


def status(*, database: str | Path | None = None) -> dict:
    with _layer(database) as layer:
        all_records = _records(layer)
        active = _current(all_records, datetime.now(timezone.utc))
        boots = layer.store.fetchone("SELECT COUNT(*) AS n FROM sessions")["n"]
    return {
        "scope": "local_single_user_only",
        "records_all_time": len(all_records), "records_active": len(active),
        "memory_window_hours": ACTIVE_HOURS,
        "retention_note": "48 hours is a retrieval window, not data deletion. SQLite persists until the operator removes the local DB and mirror.",
        "core_sessions": boots, "verified_facts": 0,
    }
