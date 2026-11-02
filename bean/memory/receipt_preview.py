"""Bounded read-only preview hook for versioned BEAN Core execution receipts.

Call from an already initialized Python Core terminal/UI. No event writes,
model calls, background polling, second database, or implied equivalence.
This is an inspection window, not a comprehensive search index.
"""
from __future__ import annotations

from .receipt_contract import _uuid, receipt_from_event
from .store import get_store


def recent_receipt_preview(*, limit: int = 10, scan_limit: int = 200,
                           correlation_id: str | None = None,
                           related_to_event_id: str | None = None) -> dict:
    """Return privacy-bounded receipts from existing SQLite events, newest first.

    `related_to_event_id` matches only explicit recorded relations pointing
    to that UUID. Similar actions or modules are never treated as equivalent.
    `scan_limit_reached` means older events might contain additional matches.
    """
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer from 1 to 50")
    if type(scan_limit) is not int or not limit <= scan_limit <= 500:
        raise ValueError("scan_limit must be an integer from limit to 500")
    if correlation_id is not None:
        correlation_id = _uuid(correlation_id)
    if related_to_event_id is not None:
        related_to_event_id = _uuid(related_to_event_id)

    # Reuse the initialized canonical store; never open another SQLite
    # connection or reconcile/mutate the mirror as a side effect.
    rows = get_store().fetchall(
        "SELECT event_uuid, created_at, source, data "
        "FROM events ORDER BY id DESC LIMIT ?", (scan_limit,)
    )
    receipts = []
    skipped = 0
    scanned = 0
    for row in rows:
        scanned += 1
        try:
            item = receipt_from_event(row)
        except (ValueError, TypeError, KeyError):
            # Legacy and invalid rows are not evidence of a v1 receipt.
            # Never echo their unvalidated data or free-text summaries.
            skipped += 1
            continue
        if correlation_id is not None and item["correlation_id"] != correlation_id:
            continue
        if related_to_event_id is not None and not any(
            link["target_event_id"] == related_to_event_id
            for link in item["relations"]
        ):
            continue
        receipts.append({
            "event_id": item["event_id"],
            "timestamp": item["timestamp"],
            "source": item["source"],
            "request_id": item["request_id"],
            "correlation_id": item["correlation_id"],
            "module": item["module"],
            "action": item["action"],
            "outcome": item["outcome"],
            "uncertainty": item["uncertainty"],
            "evidence_refs": item["evidence_refs"],
            "relations": item["relations"],
        })
        if len(receipts) == limit:
            break

    return {
        "schema": "bean.receipt_preview.v1",
        "status": "observed" if receipts else "no_matches_in_window",
        "read_only": True,
        "scanned": scanned,
        "skipped_legacy_or_invalid": skipped,
        "scan_limit_reached": scanned == scan_limit,
        "result_limit_reached": len(receipts) == limit,
        "receipts": receipts,
    }
