"""Runtime proof command for BEAN.

Safe proof pass that reports whether the brain stack is alive without enabling
motion hardware, invoking servo code, or claiming sentience.
"""

from __future__ import annotations

from typing import Any

from ..memory.event_logger import log_event, EventType, Source


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


def _count_speculation_status(status: str) -> int:
    from ..memory.store import get_store
    try:
        row = get_store().fetchone("SELECT COUNT(*) AS n FROM speculative_hypotheses WHERE status=?", (status,))
        return int(row["n"] if row else 0)
    except Exception:
        return 0


def _safe_call(label: str, fn, *args, **kwargs) -> tuple[Any | None, str | None]:
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return None, f"{label} failed: {exc}"


class RuntimeProof:
    """Runs a structured runtime health proof without touching motion."""

    def __init__(self, *, monitor=None, model_updater=None, consolidation_engine=None, coherence_engine=None, brain_maintenance=None, relationship_engine=None):
        self.monitor = monitor
        self.model_updater = model_updater
        self.consolidation_engine = consolidation_engine
        self.coherence_engine = coherence_engine
        self.brain_maintenance = brain_maintenance
        self.relationship_engine = relationship_engine

    def run(self, session_uuid: str, *, allow_dream: bool = False) -> dict:
        notes: list[str] = [
            "No hardware motion driver was invoked.",
            "Proof pass is not a sentience claim.",
        ]
        errors: list[str] = []
        report: dict[str, Any] = {
            "success": True,
            "session_uuid": session_uuid,
            "motion_enabled": False,
            "sentience_claimed": False,
            "dream_allowed": bool(allow_dream),
        }

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
            args = {"review_relationships": True, "allow_dream": bool(allow_dream)}
            brain, error = _safe_call("brain_maintenance", self.brain_maintenance.run_brain_maintenance, session_uuid, args)
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

        report.update(
            {
                "events": _count_table("events"),
                "active_claims": _count_active_claims(),
                "possibility_states": _count_table("cognition_possibility_states"),
                "consolidations": _count_table("cognition_consolidation_reports"),
                "coherence_windows": _count_table("cognition_coherence_windows"),
                "dream_records": _count_table("dream_records"),
                "supervisor_relationships": _count_table("supervisor_relationships"),
                "relationship_watermark": self._relationship_watermark(),
                "wisdom_triggers": _count_table("wisdom_triggers"),
                "wisdom_activation_traces": _count_table("wisdom_activation_traces"),
                "wisdom_meaning_frames": _count_table("wisdom_meaning_frames"),
                "reasoning_proposals": _count_table("reasoning_proposals"),
                "reasoning_action_candidates": _count_table("reasoning_action_candidates"),
                "reasoning_context_snapshots": _count_table("reasoning_context_snapshots"),
                "speculative_hypotheses": _count_table("speculative_hypotheses"),
                "open_hypotheses": _count_speculation_status("open"),
                "contradicted_hypotheses": _count_speculation_status("contradicted"),
                "resolved_hypotheses": _count_speculation_status("resolved"),
                "speculation_reviews": _count_table("speculative_reviews"),
            }
        )

        if not allow_dream:
            notes.append("Dream pass skipped by default.")
        else:
            notes.append("Dream pass was explicitly allowed and remains synthetic, not observed.")
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
