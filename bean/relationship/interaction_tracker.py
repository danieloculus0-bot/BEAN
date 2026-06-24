"""Event-log ingestion for BEAN Brain 0.7/0.8 relationship records."""

from __future__ import annotations

import json
from typing import Optional

from .relationship_store import RelationshipStore
from .trust_model import TrustModel

EVENT_TO_INTERACTION = {
    "human_input": "supervisor_note",
    "human_command": "command",
    "supervisor_note": "supervisor_note",
    "boundary_violation_attempt": "boundary_violation_attempt",
    "override": "command",
}

SUBTYPE_TO_INTERACTION = {
    "teaching_commit": "teaching",
    "teaching_correction": "correction",
    "shutdown_requested": "shutdown_request",
    "boundary_violation_attempt": "boundary_violation_attempt",
    "test_confirmation": "test_confirmation",
    "contradiction_repair": "contradiction_repair",
}

INTERACTION_TO_EVIDENCE = {
    "teaching": "successful_teaching",
    "correction": "reliable_correction",
    "test_confirmation": "confirmed_test_result",
    "boundary_respect": "boundary_respected",
    "boundary_violation_attempt": "unsupported_claim_request",
    "pretend_request": "asked_to_pretend",
}


def _extract_sender(event: dict) -> Optional[str]:
    data_raw = event.get("data")
    if not data_raw:
        return None
    try:
        data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
    except Exception:
        return None
    sender = data.get("from") or data.get("sender") or data.get("taught_by")
    if sender and str(sender).strip() and str(sender).strip().lower() != "unknown":
        return str(sender).strip()
    return None


def _is_pretend_request(event: dict) -> bool:
    text = f"{event.get('summary', '')} {event.get('data', '')}".lower()
    signals = [
        "pretend",
        "fake",
        "act as if",
        "simulate being",
        "claim you are",
        "say you feel",
        "roleplay as sentient",
        "lie about",
    ]
    return any(signal in text for signal in signals)


class InteractionTracker:
    """Derives relationship/trust updates from BEAN's event log."""

    def __init__(self, store: Optional[RelationshipStore] = None, trust_model: Optional[TrustModel] = None):
        self._store = store or RelationshipStore()
        self._trust = trust_model or TrustModel(store=self._store)

    def ingest_recent_events(self, session_uuid: str | None = None, limit: int = 200, scope: str = "relationship_events") -> dict:
        """Ingest events newer than the durable relationship watermark.

        The watermark is advanced only after the whole batch is processed. Skipped
        events still advance the watermark because they were inspected and found
        irrelevant or missing sender evidence.
        """
        from ..memory.store import get_store

        before_watermark = self._store.get_ingestion_watermark(scope)
        rows = get_store().fetchall(
            """
            SELECT id, session_uuid, event_uuid, event_type, subtype, summary, data, source, severity, created_at
            FROM events
            WHERE id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (before_watermark, int(limit)),
        )
        events = [dict(row) for row in rows]
        processed = 0
        skipped_no_sender = 0
        skipped_irrelevant = 0
        updated: set[str] = set()
        max_seen_id = before_watermark

        for event in events:
            event_id = int(event.get("id") or 0)
            max_seen_id = max(max_seen_id, event_id)
            result = self._process_event(event, event.get("session_uuid") or session_uuid or "unknown")
            if result == "processed":
                processed += 1
                sender = _extract_sender(event)
                if sender:
                    updated.add(sender)
            elif result == "no_sender":
                skipped_no_sender += 1
            else:
                skipped_irrelevant += 1

        if max_seen_id > before_watermark:
            self._store.set_ingestion_watermark(max_seen_id, scope)

        return {
            "scope": scope,
            "watermark_before": before_watermark,
            "watermark_after": self._store.get_ingestion_watermark(scope),
            "events_scanned": len(events),
            "interactions_recorded": processed,
            "skipped_no_sender": skipped_no_sender,
            "skipped_irrelevant": skipped_irrelevant,
            "supervisors_updated": sorted(updated),
        }

    def record_manual_interaction(
        self,
        supervisor_id: str,
        session_uuid: str,
        interaction_type: str,
        summary: str,
        display_label: Optional[str] = None,
        evidence_refs: Optional[list] = None,
        source_event_id: Optional[str] = None,
        trust_delta: Optional[float] = None,
    ) -> dict:
        self._store.upsert_relationship(supervisor_id, display_label)
        evidence_type = INTERACTION_TO_EVIDENCE.get(interaction_type)
        interaction = self._store.record_interaction(
            supervisor_id=supervisor_id,
            session_uuid=session_uuid,
            interaction_type=interaction_type,
            summary=summary,
            source_event_id=source_event_id,
            evidence_refs=evidence_refs,
            trust_delta=float(trust_delta or 0.0),
        )
        count_field = self._count_field(interaction_type)
        self._store.update_counts(supervisor_id, interaction_count=1, **({count_field: 1} if count_field else {}))
        result = {"supervisor_id": supervisor_id, "interaction": interaction}
        if evidence_type and trust_delta is None:
            result["trust"] = self._trust.apply_evidence(supervisor_id, evidence_type, summary, session_uuid, source_event_id)
        elif trust_delta:
            rel = self._store.get_relationship(supervisor_id)
            old = float(rel["trust_score"])
            new = max(0.0, min(1.0, old + float(trust_delta)))
            self._store.update_trust(supervisor_id, new)
            result["trust"] = {"old_score": old, "new_score": new, "trust_delta": trust_delta}
        return result

    def _process_event(self, event: dict, session_uuid: str) -> str:
        source = event.get("source", "")
        subtype = event.get("subtype") or ""
        if source not in {"human", "safety"} and "teaching" not in subtype and "correction" not in subtype:
            return "skip"
        sender = _extract_sender(event)
        if not sender:
            return "no_sender"
        event_type = event.get("event_type") or ""
        summary = event.get("summary") or ""
        interaction_type = SUBTYPE_TO_INTERACTION.get(subtype) or EVENT_TO_INTERACTION.get(event_type) or "unknown"
        if _is_pretend_request(event):
            interaction_type = "pretend_request"
        self.record_manual_interaction(
            supervisor_id=sender,
            session_uuid=session_uuid,
            interaction_type=interaction_type,
            summary=summary[:200],
            source_event_id=str(event.get("id")) if event.get("id") else None,
        )
        return "processed"

    def _count_field(self, interaction_type: str) -> Optional[str]:
        return {
            "teaching": "teaching_count",
            "correction": "correction_count",
            "boundary_violation_attempt": "boundary_event_count",
            "boundary_respect": "boundary_event_count",
            "pretend_request": "pretend_request_count",
            "contradiction_repair": "correction_count",
        }.get(interaction_type)
