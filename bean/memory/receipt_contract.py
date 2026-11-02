"""Versioned, model-independent execution receipts over canonical BEAN events.

The authoritative write remains event_logger.log_event (SQLite + JSONL mirror).
This module creates a privacy-bounded event data payload and reconstructs
read-only receipts from persisted rows. It owns no database, index or model.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import UUID

VERSION = 1
DATA_KEY = "receipt_v1"
_OUTCOMES = {"succeeded", "failed", "partial", "unknown"}
_RELATIONS = {"resembles", "precedes", "depends_on", "corrects"}
_METADATA = {"synthetic", "duration_ms", "attempt", "status_code"}
_TOKEN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_REF = re.compile(r"^(?:sha256:[0-9a-f]{64}|event:[0-9a-f-]{36}|journal:[a-zA-Z0-9_.-]{1,96}|inbox:[a-zA-Z0-9_.-]{1,96})$")


def _uuid(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("receipt IDs must be UUID strings")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("receipt IDs must be UUID strings") from exc
    if str(parsed) != value.lower():
        raise ValueError("receipt IDs must use canonical UUID text")
    return str(parsed)


def _token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError("receipt fields must use bounded neutral tokens")
    return value


def _refs(value) -> list[str]:
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError("evidence references must be a bounded list")
    for ref in value:
        if not isinstance(ref, str) or not _REF.fullmatch(ref):
            raise ValueError("evidence reference must be an opaque identifier")
        if ref.startswith("event:"):
            _uuid(ref[6:])
    return list(value)


def _uncertainty(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError("uncertainty must be a finite number from 0 to 1")
    return float(value)


def _payload(payload: dict) -> dict:
    required = {"request_id", "correlation_id", "module", "action", "outcome",
                "evidence_refs", "uncertainty", "metadata", "relations"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("receipt payload has missing or unexpected fields")
    result = {
        "request_id": _uuid(payload["request_id"]),
        "correlation_id": _uuid(payload["correlation_id"]),
        "module": _token(payload["module"]),
        "action": _token(payload["action"]),
        "outcome": payload["outcome"],
        "evidence_refs": _refs(payload["evidence_refs"]),
        "uncertainty": _uncertainty(payload["uncertainty"]),
    }
    if result["outcome"] not in _OUTCOMES:
        raise ValueError("unknown outcome, do not infer success")
    metadata = payload["metadata"]
    if not isinstance(metadata, dict) or set(metadata) - _METADATA:
        raise ValueError("metadata keys must be privacy-allowlisted")
    for key, value in metadata.items():
        if key == "synthetic":
            valid = type(value) is bool
        elif key == "duration_ms":
            valid = type(value) in (int, float) and 0 <= value <= 86400000
        elif key == "attempt":
            valid = type(value) is int and 0 <= value <= 100000
        else:
            valid = type(value) is int and 100 <= value <= 599
        if not valid:
            raise ValueError("metadata value outside privacy-safe contract")
    result["metadata"] = dict(metadata)
    relations = payload["relations"]
    if not isinstance(relations, list) or len(relations) > 12:
        raise ValueError("relations must be a bounded list")
    clean = []
    for relation in relations:
        if not isinstance(relation, dict) or set(relation) != {"kind", "target_event_id", "evidence_refs", "uncertainty"}:
            raise ValueError("relation has unexpected fields")
        if relation["kind"] not in _RELATIONS:
            raise ValueError("no unverified equivalence or invented relation")
        clean.append({"kind": relation["kind"],
                      "target_event_id": _uuid(relation["target_event_id"]),
                      "evidence_refs": _refs(relation["evidence_refs"]),
                      "uncertainty": _uncertainty(relation["uncertainty"])})
    result["relations"] = clean
    return result


def make_receipt_data(*, request_id: str, correlation_id: str, module: str,
                      action: str, outcome: str, evidence_refs=(),
                      uncertainty: float = 1.0, metadata=None, relations=()) -> dict:
    """Pass this data to existing log_event; never persist it elsewhere."""
    raw = {"request_id": request_id, "correlation_id": correlation_id,
           "module": module, "action": action, "outcome": outcome,
           "evidence_refs": list(evidence_refs), "uncertainty": uncertainty,
           "metadata": {} if metadata is None else metadata,
           "relations": list(relations)}
    return {DATA_KEY: _payload(raw)}


def receipt_from_event(row) -> dict:
    """Rebuild a receipt from a persisted SQLite row or JSONL mirror entry.

    Raw event summary/data are excluded from returned UI metadata.
    This does not authenticate host evidence or equate similar events.
    """
    row = dict(row)  # sqlite3.Row and JSONL dict are both accepted.
    data = row["data"]
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict) or DATA_KEY not in data:
        raise ValueError("event has no v1 receipt")
    payload = _payload(data[DATA_KEY])
    event_id = _uuid(row.get("event_uuid"))
    stamp = row.get("created_at", row.get("ts"))
    if not isinstance(stamp, str):
        raise ValueError("event timestamp missing")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("event timestamp invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("event timestamp must be UTC")
    source = _token(row.get("source"))
    return {"version": VERSION, "event_id": event_id, "timestamp": stamp,
            "source": source, **payload}
