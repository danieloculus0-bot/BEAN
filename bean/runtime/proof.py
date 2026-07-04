"""Runtime proof command for BEAN."""

from __future__ import annotations

from typing import Any

from ..memory.event_logger import EventType, Source, log_event


COUNT_TABLES = {
    "events": "events",
    "possibility_states": "cognition_possibility_states",
    "consolidations": "cognition_consolidations",
    "coherence_windows": "cognition_coherence_windows",
    "dream_records": "dream_records",
    "supervisor_relationships": "supervisor_relationships",
    "wisdom_activation_traces": "wisdom_activation_traces",
    "wisdom_meaning_frames": "wisdom_meaning_frames",
    "wisdom_repair_attempts": "wisdom_repair_attempts",
    "wisdom_loop_signatures": "wisdom_loop_signatures",
    "reasoning_context_packets": "reasoning_context_packets",
    "reasoning_requests": "reasoning_requests",
    "reasoning_responses": "reasoning_responses",
    "reasoning_proposals": "reasoning_proposals",
    "reasoning_filter_results": "reasoning_filter_results",
    "speculative_hypotheses": "speculative_hypotheses",
    "speculative_reviews": "speculative_reviews",
}


def _count_table(table: str) -> int:
    from ..memory.store import get_store
    try:
        row = get_store().fetchone(f"SELECT COUNT(*) AS n FROM {table}")
        return int(row["n"] if row else 0)
    except Exception:
        return 0


def _count_active_claims() -> int:
    from ..memory.store import get_store
    try:
        row = get_store().fetchone("SELECT COUNT(*) AS n FROM world_claims WHERE active=1")
        return int(row["n"] if row else 0)
    except Exception:
        return 0


def _safe_call(label: str, fn, *args, **kwargs) -> tuple[Any | None, str | None]:
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return None, f"{label} failed: {exc}"


class RuntimeProof:
    """Runs a structured health proof without touching motion hardware."""

    def __init__(self, *, monitor=None, model_updater=None, consolidation_engine=None, coherence_engine=None, brain_maintenance=None, relationship_engine=None):
        self.monitor = monitor
        self.model_updater = model_updater
        self.consolidation_engine = consolidation_engine
        self.coherence_engine = coherence_engine
        self.brain_maintenance = brain_maintenance
        self.relationship_engine = relationship_engine

    def run(self, session_uuid: str, *, allow_dream: bool = False) -> dict:
        notes = ["No hardware motion driver was invoked."]
        errors = []
        report = {"success": True, "session_uuid": session_uuid, "motion_enabled": False, "dream_allowed": bool(allow_dream)}

        if self.monitor is not None:
            reading, error = _safe_call("monitor", lambda: self.monitor.read().to_dict())
            if error:
                errors.append(error)
            else:
                report["status_snapshot"] = reading

        if self.model_updater is not None:
            update, error = _safe_call("model_update", self.model_updater.run, session_uuid, trigger="runtime_proof")
            if error:
                errors.append(error)
            else:
                report["model_update"] = update

        if self.coherence_engine is not None:
            coherence, error = _safe_call("coherence", self.coherence_engine.run, session_uuid, trigger="runtime_proof")
            if error:
                errors.append(error)
            else:
                report["coherence"] = coherence.to_dict() if hasattr(coherence, "to_dict") else coherence

        if self.consolidation_engine is not None:
            consolidation, error = _safe_call("consolidation", self.consolidation_engine.run, session_uuid, trigger="runtime_proof")
            if error:
                errors.append(error)
            else:
                report["consolidation"] = consolidation.to_dict() if hasattr(consolidation, "to_dict") else consolidation

        if self.brain_maintenance is not None:
            brain, error = _safe_call(
                "brain_maintenance",
                self.brain_maintenance.run_brain_maintenance,
                session_uuid,
                {"review_relationships": True, "allow_dream": bool(allow_dream)},
            )
            if error:
                errors.append(error)
            else:
                report["brain_maintenance"] = brain
        elif self.relationship_engine is not None:
            relationships, error = _safe_call("relationship_maintenance", self.relationship_engine.run, session_uuid=session_uuid, event_limit=200)
            if error:
                errors.append(error)
            else:
                report["relationship_maintenance"] = relationships

        report["active_claims"] = _count_active_claims()
        for key, table in COUNT_TABLES.items():
            report[key] = _count_table(table)
        report["relationship_watermark"] = self._relationship_watermark()

        if allow_dream:
            notes.append("Dream pass was explicitly allowed and remains synthetic.")
        else:
            notes.append("Dream pass skipped by default.")
        report["notes"] = notes
        report["errors"] = errors
        if errors:
            report["success"] = False

        log_event(
            session_uuid=session_uuid,
            event_type=EventType.MEMORY_CONSOLIDATION,
            summary="Runtime proof pass complete.",
            source=Source.SYSTEM,
            subtype="runtime_proof",
            data=report,
        )
        return report

    def _relationship_watermark(self) -> int:
        try:
            from ..relationship.relationship_store import RelationshipStore
            return RelationshipStore().get_ingestion_watermark()
        except Exception:
            return 0
