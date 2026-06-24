"""Relationship maintenance orchestration for BEAN Brain 0.7/0.8."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .interaction_tracker import InteractionTracker
from .relationship_store import RelationshipStore
from .supervisor_record import SupervisorRecordBuilder
from .trust_model import TrustModel


class RelationshipMaintenanceEngine:
    """Ingest recent events, run trust reviews, and return relationship summaries."""

    def __init__(self, store: Optional[RelationshipStore] = None):
        self._store = store or RelationshipStore()
        self._trust = TrustModel(store=self._store)
        self._tracker = InteractionTracker(store=self._store, trust_model=self._trust)
        self._builder = SupervisorRecordBuilder(store=self._store)

    @property
    def store(self) -> RelationshipStore:
        return self._store

    @property
    def tracker(self) -> InteractionTracker:
        return self._tracker

    @property
    def trust_model(self) -> TrustModel:
        return self._trust

    @property
    def records(self) -> SupervisorRecordBuilder:
        return self._builder

    def run(self, session_uuid: str, event_limit: int = 200) -> dict:
        before_watermark = self._store.get_ingestion_watermark()
        ingest = self._tracker.ingest_recent_events(session_uuid=session_uuid, limit=event_limit)
        reviews = self._trust.run_all_reviews()
        records = self._builder.build_all_active()
        after_watermark = self._store.get_ingestion_watermark()
        report = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "session_uuid": session_uuid,
            "event_limit": int(event_limit),
            "watermark_before": before_watermark,
            "watermark_after": after_watermark,
            "ingest": ingest,
            "trust_reviews": reviews,
            "active_supervisors": len(records),
            "supervisor_summaries": [
                {
                    "supervisor_id": record.supervisor_id,
                    "trust_score": round(record.trust_score, 4),
                    "trust_status": record.trust_status,
                    "interaction_count": record.interaction_count,
                }
                for record in records
            ],
        }
        self._log(session_uuid, report)
        return report

    def _log(self, session_uuid: str, report: dict):
        try:
            from ..memory.event_logger import log_event, EventType, Source
            log_event(
                session_uuid=session_uuid,
                event_type=EventType.MEMORY_CONSOLIDATION,
                summary=(
                    f"Relationship maintenance: {report['active_supervisors']} supervisor(s) active, "
                    f"{report['ingest'].get('interactions_recorded', 0)} new interaction(s) recorded, "
                    f"watermark {report['watermark_before']}->{report['watermark_after']}, "
                    f"{len(report['trust_reviews'])} trust review(s) run."
                ),
                source=Source.SYSTEM,
                subtype="relationship_maintenance",
                data=report,
            )
        except Exception:
            pass
