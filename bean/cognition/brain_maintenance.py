"""Brain Maintenance for BEAN Brain 0.6/0.7.

Manual/runtime orchestration for Brain 0.3 through 0.7 systems.
This layer exposes safe maintenance passes without enabling motion, hardware
actuation, fake emotion, or sentience claims.
"""

from __future__ import annotations

from typing import Any, Optional

from ..memory.event_logger import log_event, EventType, Source, Severity, get_recent_events
from .epistemic_guard import CandidateClaim, EpistemicGuard
from .contradiction_court import ContradictionCourt
from .falsification import FalsificationEngine
from .dreaming import DreamEngine, DreamType
from .uncertainty_garden import UncertaintyGarden, UncertaintyRecord
from .dignity import DignityLayer
from .inner_weather import InnerWeatherEngine
from .autobiography import AutobiographyEngine


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


class BrainMaintenanceEngine:
    """Single safe orchestration facade for manual brain maintenance commands."""

    def __init__(self):
        self.epistemic_guard = EpistemicGuard()
        self.contradiction_court = ContradictionCourt()
        self.falsification_engine = FalsificationEngine()
        self.dream_engine = DreamEngine()
        self.uncertainty_garden = UncertaintyGarden()
        self.dignity_layer = DignityLayer()
        self.inner_weather = InnerWeatherEngine()
        self.autobiography = AutobiographyEngine()
        try:
            from ..relationship.maintenance import RelationshipMaintenanceEngine
            self.relationships = RelationshipMaintenanceEngine()
        except Exception:
            self.relationships = None

    def run_epistemic_audit(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        if args.get("text") or args.get("content"):
            candidate = CandidateClaim(
                key=str(args.get("key") or "candidate.language_output"),
                content=str(args.get("content") or args.get("text")),
                source_type=args.get("source_type") or "inbox_candidate",
                source_ref=args.get("source_ref"),
                confidence=args.get("confidence"),
                evidence=args.get("evidence") or ([] if not args.get("source_ref") else [str(args.get("source_ref"))]),
                falsification_path=args.get("falsification_path"),
                metadata=args.get("metadata") or {},
            )
            audit = self.epistemic_guard.audit(candidate)
            report = {"mode": "candidate", "audit": audit.to_dict()}
        else:
            audits = self.epistemic_guard.audit_active_claims(limit=int(args.get("limit", 200)))
            report = {"mode": "active_claims", "count": len(audits), "audits": [a.to_dict() for a in audits]}
        self._log(session_uuid, "epistemic_audit", "Epistemic audit complete.", report, EventType.WORLD_MODEL_UPDATE)
        return report

    def run_contradiction_court(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        report = self.contradiction_court.run(session_uuid=session_uuid)
        report["open_conflicts"] = self.contradiction_court.open_conflicts()
        return report

    def run_falsification_check(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        results = self.falsification_engine.check_all(session_uuid=session_uuid)
        return {"count": len(results), "falsified_count": len([r for r in results if r.falsified]), "results": [r.to_dict() for r in results]}

    def run_dream_pass(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        try:
            dream_type = DreamType(str(args.get("dream_type") or DreamType.COMPRESSION.value))
        except ValueError:
            dream_type = DreamType.COMPRESSION
        record = self.dream_engine.run_pass(session_uuid, dream_type=dream_type, limit=int(args.get("limit", 25)))
        report = record.to_dict()
        self._log(session_uuid, "dream_pass", "Dream pass generated synthetic artifact.", report, EventType.MEMORY_CONSOLIDATION)
        return report

    def plant_uncertainty(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        raw_options = args.get("options") or ["unresolved", "requires evidence"]
        options: list[tuple[str, float]] = []
        for opt in raw_options:
            if isinstance(opt, dict):
                options.append((str(opt.get("interpretation") or opt.get("label") or opt.get("key") or "option"), float(opt.get("weight", 1.0))))
            else:
                options.append((str(opt), 1.0))
        record = UncertaintyRecord(
            question=str(args.get("question") or "Unspecified uncertainty"),
            what_would_resolve_it=str(args.get("what_would_resolve_it") or args.get("resolution_path") or "Supervisor or sensor evidence is required."),
            significance=float(args.get("significance", 0.5)),
            decay_rate=float(args.get("decay_rate", 0.01)),
        )
        self.uncertainty_garden.plant(record, options)
        self.uncertainty_garden.normalize(record.uncertainty_id)
        report = {"uncertainty": record.to_dict(), "options": self.uncertainty_garden.options(record.uncertainty_id)}
        self._log(session_uuid, "plant_uncertainty", f"Uncertainty planted: {record.question}", report, EventType.CURIOSITY)
        return report

    def review_uncertainties(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        open_items = self.uncertainty_garden.open_uncertainties()
        reports = [self.uncertainty_garden.review(item["uncertainty_id"]) for item in open_items[: int(args.get("limit", len(open_items) or 0))]]
        report = {"open_count": len(open_items), "reviewed_count": len(reports), "reviews": reports}
        self._log(session_uuid, "review_uncertainties", "Uncertainty garden review complete.", report, EventType.CURIOSITY)
        return report

    def resolve_uncertainty(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        uncertainty_id = args.get("uncertainty_id")
        selected_option_id = args.get("selected_option_id") or args.get("option_id")
        reason = str(args.get("reason") or "manual resolution")
        if not uncertainty_id or not selected_option_id:
            return {"success": False, "reason": "missing uncertainty_id or selected_option_id"}
        success = self.uncertainty_garden.resolve(str(uncertainty_id), str(selected_option_id), reason)
        report = {"success": success, "uncertainty_id": uncertainty_id, "selected_option_id": selected_option_id, "reason": reason}
        self._log(session_uuid, "resolve_uncertainty", "Uncertainty resolution attempted.", report, EventType.CURIOSITY)
        return report

    def run_dignity_check(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        text = args.get("text")
        if text is None:
            recent = get_recent_events(session_uuid, int(args.get("limit", 20)))
            text = "\n".join(e.get("summary", "") for e in recent if e.get("source") == "human" or e.get("event_type") in {"human_input", "human_command", "supervisor_note"})
        events = self.dignity_layer.evaluate_text(str(text or ""), source_event_id=args.get("source_event_id"))
        report = {"trigger_count": len(events), "events": [e.to_dict() for e in events]}
        self._log(session_uuid, "dignity_check", "Dignity check complete.", report, EventType.SUPERVISOR_NOTE)
        return report

    def run_inner_weather(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        report = self.inner_weather.generate(session_uuid).to_dict()
        self._log(session_uuid, "inner_weather", "Inner weather pressure report generated.", report, EventType.SELF_MODEL_UPDATE)
        return report

    def run_autobiography_snapshot(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        entries = self.autobiography.build_snapshot(session_uuid)
        report = {"entry_count": len(entries), "entries": [e.to_dict() for e in entries]}
        self._log(session_uuid, "autobiography_snapshot", "Autobiographical snapshot generated.", report, EventType.SELF_MODEL_UPDATE)
        return report

    def run_relationship_maintenance(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        if self.relationships is None:
            return {"success": False, "reason": "relationship engine unavailable"}
        return self.relationships.run(session_uuid=session_uuid, event_limit=int(args.get("event_limit", 200)))

    def run_brain_maintenance(self, session_uuid: str, args: Optional[dict] = None) -> dict:
        args = args or {}
        report: dict[str, Any] = {
            "contradiction_court": self.run_contradiction_court(session_uuid, args),
            "falsification": self.run_falsification_check(session_uuid, args),
            "inner_weather": self.run_inner_weather(session_uuid, args),
            "autobiography": self.run_autobiography_snapshot(session_uuid, args),
        }
        if _as_bool(args.get("review_uncertainties"), default=False):
            report["uncertainty_review"] = self.review_uncertainties(session_uuid, args)
        if _as_bool(args.get("allow_dream"), default=False):
            report["dream"] = self.run_dream_pass(session_uuid, args)
        if _as_bool(args.get("review_relationships"), default=False):
            report["relationships"] = self.run_relationship_maintenance(session_uuid, args)
        if args.get("text"):
            report["dignity"] = self.run_dignity_check(session_uuid, args)
        self._log(session_uuid, "brain_maintenance", "Brain maintenance pass complete.", report, EventType.MEMORY_CONSOLIDATION)
        return report

    def _log(self, session_uuid: str, subtype: str, summary: str, data: dict, event_type: EventType, severity: Severity = Severity.INFO):
        log_event(session_uuid, event_type, summary, Source.SYSTEM, subtype=subtype, data=data, severity=severity)
