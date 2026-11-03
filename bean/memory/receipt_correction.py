"""Read-only builder for append-only corrections to canonical BEAN receipts.

This does not write events or supersede existing rows. Callers must pass the
result to event_logger.log_event to append a separate factual correction.
Opaque evidence identifiers are not independently authenticated here.
"""
from __future__ import annotations

from .receipt_contract import _uuid, make_receipt_data, receipt_from_event
from .store import get_store


def correction_data_for_event(*, target_event_id: str, request_id: str,
                              outcome: str, evidence_refs,
                              uncertainty: float = 1.0,
                              action: str = "correct_observation",
                              metadata=None) -> dict:
    """Build v1 receipt data correcting a *persisted* v1 event, without writes.

    The original event's correlation and module are preserved. A correction
    needs at least one non-event evidence reference; it never asserts that
    source evidence is verified or that two observations are equivalent.
    """
    target_id = _uuid(target_event_id)
    row = get_store().fetchone(
        "SELECT event_uuid, created_at, source, data FROM events WHERE event_uuid=?",
        (target_id,),
    )
    if row is None:
        raise ValueError("correction target is not a persisted event")
    original = receipt_from_event(row)
    refs = list(evidence_refs)
    if not any(isinstance(ref, str) and not ref.startswith("event:") for ref in refs):
        raise ValueError("correction requires non-event evidence reference")
    relation = {"kind": "corrects", "target_event_id": target_id,
                "evidence_refs": refs, "uncertainty": uncertainty}
    return make_receipt_data(
        request_id=request_id,
        correlation_id=original["correlation_id"],
        module=original["module"], action=action, outcome=outcome,
        evidence_refs=refs, uncertainty=uncertainty,
        metadata={} if metadata is None else metadata,
        relations=[relation],
    )
