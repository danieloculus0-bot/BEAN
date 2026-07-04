"""
bean/runtime/inbox_handlers.py

Built-in handlers for file-based runtime inbox commands.
"""

from __future__ import annotations

from ..memory.event_logger import EventType, Source, log_event
from .inbox import InboxMessage


def make_handlers(
    loop=None,
    teaching_layer=None,
    monitor=None,
    ctx: dict | None = None,
    *,
    model_updater=None,
    consolidation_engine=None,
    coherence_engine=None,
    state_manager=None,
    brain_maintenance=None,
    relationship_engine=None,
) -> dict:
    ctx = ctx or {}

    def _brain():
        nonlocal brain_maintenance
        if brain_maintenance is None:
            from ..cognition.brain_maintenance import BrainMaintenanceEngine
            brain_maintenance = BrainMaintenanceEngine()
        return brain_maintenance

    def _relationship():
        nonlocal relationship_engine
        if relationship_engine is None:
            from ..relationship.maintenance import RelationshipMaintenanceEngine
            relationship_engine = RelationshipMaintenanceEngine()
        return relationship_engine

    def status(msg: InboxMessage, session_uuid: str) -> dict:
        reading = monitor.read().to_dict() if monitor is not None else None
        loop_status = loop.status() if loop is not None else {}
        model_snapshot = model_updater.full_snapshot() if model_updater is not None else None
        possibility_snapshot = state_manager.snapshot() if state_manager is not None else None
        return {"status": "running", "loop": loop_status, "hardware": reading, "models": model_snapshot, "possibility_states": possibility_snapshot}

    def log_note(msg: InboxMessage, session_uuid: str) -> dict:
        text = str(msg.args.get("text", ""))
        log_event(session_uuid, EventType.SUPERVISOR_NOTE, text or "Supervisor note received.", Source.HUMAN, subtype="runtime_note", data={"text": text, "from": msg.sender})
        return {"logged": True}

    def shutdown(msg: InboxMessage, session_uuid: str) -> dict:
        reason = str(msg.args.get("reason", "inbox_shutdown"))
        if loop is not None:
            loop.request_shutdown(reason=reason)
        return {"shutdown_requested": True, "reason": reason}

    def run_reflection(msg: InboxMessage, session_uuid: str) -> dict:
        from ..reflection.reflect import run_reflection
        result = run_reflection(session_uuid, trigger_type="manual")
        if model_updater is not None:
            result = {"reflection": result, "model_update": model_updater.run(session_uuid, trigger="post_reflection")}
        if consolidation_engine is not None:
            result["consolidation"] = consolidation_engine.run(session_uuid, trigger="post_reflection").to_dict()
        return result

    def replay_skill(msg: InboxMessage, session_uuid: str) -> dict:
        if teaching_layer is None:
            return {"success": False, "reason": "teaching_layer unavailable"}
        skill_name = msg.args.get("skill_name") or msg.args.get("name")
        if not skill_name:
            return {"success": False, "reason": "missing skill_name"}
        result = teaching_layer.replay_skill(str(skill_name), session_uuid=session_uuid)
        if model_updater is not None:
            result["model_update"] = model_updater.run(session_uuid, trigger="skill_replay")
        if consolidation_engine is not None:
            result["consolidation"] = consolidation_engine.run(session_uuid, trigger="skill_replay").to_dict()
        return result

    def update_models(msg: InboxMessage, session_uuid: str) -> dict:
        if model_updater is None:
            return {"success": False, "reason": "model_updater unavailable"}
        trigger = str(msg.args.get("trigger") or msg.args.get("note") or "manual")
        return {"success": True, "update": model_updater.run(session_uuid, trigger=trigger)}

    def run_consolidation(msg: InboxMessage, session_uuid: str) -> dict:
        if consolidation_engine is None:
            return {"success": False, "reason": "consolidation_engine unavailable"}
        trigger = str(msg.args.get("trigger") or "manual")
        return {"success": True, "report": consolidation_engine.run(session_uuid, trigger=trigger).to_dict()}

    def run_coherence(msg: InboxMessage, session_uuid: str) -> dict:
        if coherence_engine is None:
            return {"success": False, "reason": "coherence_engine unavailable"}
        trigger = str(msg.args.get("trigger") or "manual")
        return {"success": True, "report": coherence_engine.run(session_uuid, trigger=trigger).to_dict()}

    def run_epistemic_audit(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_epistemic_audit(session_uuid, msg.args)}

    def run_contradiction_court(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_contradiction_court(session_uuid, msg.args)}

    def run_falsification_check(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_falsification_check(session_uuid, msg.args)}

    def run_dream_pass(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_dream_pass(session_uuid, msg.args)}

    def plant_uncertainty(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().plant_uncertainty(session_uuid, msg.args)}

    def review_uncertainties(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().review_uncertainties(session_uuid, msg.args)}

    def resolve_uncertainty(msg: InboxMessage, session_uuid: str) -> dict:
        return _brain().resolve_uncertainty(session_uuid, msg.args)

    def run_dignity_check(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_dignity_check(session_uuid, msg.args)}

    def run_inner_weather(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_inner_weather(session_uuid, msg.args)}

    def run_autobiography_snapshot(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_autobiography_snapshot(session_uuid, msg.args)}

    def run_brain_maintenance(msg: InboxMessage, session_uuid: str) -> dict:
        return {"success": True, "report": _brain().run_brain_maintenance(session_uuid, msg.args)}

    def record_supervisor_interaction(msg: InboxMessage, session_uuid: str) -> dict:
        args = msg.args or {}
        supervisor_id = str(args.get("supervisor_id") or msg.sender or "unknown")
        if not supervisor_id or supervisor_id == "unknown":
            return {"success": False, "reason": "missing supervisor_id"}
        result = _relationship().tracker.record_manual_interaction(
            supervisor_id=supervisor_id,
            session_uuid=session_uuid,
            interaction_type=str(args.get("interaction_type") or "unknown"),
            summary=str(args.get("summary") or "Supervisor interaction recorded."),
            display_label=args.get("display_label"),
            evidence_refs=args.get("evidence_refs") or [],
            source_event_id=args.get("source_event_id"),
            trust_delta=args.get("trust_delta"),
        )
        return {"success": True, **result}

    def show_supervisor_record(msg: InboxMessage, session_uuid: str) -> dict:
        supervisor_id = str((msg.args or {}).get("supervisor_id") or msg.sender or "")
        record = _relationship().records.build(supervisor_id)
        if record is None:
            return {"status": "no_record", "supervisor_id": supervisor_id}
        return record.to_dict()

    def run_trust_review(msg: InboxMessage, session_uuid: str) -> dict:
        supervisor_id = (msg.args or {}).get("supervisor_id")
        if supervisor_id:
            return _relationship().trust_model.run_review(str(supervisor_id))
        return {"reviews": _relationship().trust_model.run_all_reviews()}

    def list_supervisors(msg: InboxMessage, session_uuid: str) -> dict:
        records = [record.to_dict() for record in _relationship().records.build_all_active()]
        return {"active_supervisor_count": len(records), "supervisors": records}

    def run_relationship_maintenance(msg: InboxMessage, session_uuid: str) -> dict:
        limit = int((msg.args or {}).get("event_limit", 200))
        return _relationship().run(session_uuid=session_uuid, event_limit=limit)

    def run_runtime_proof(msg: InboxMessage, session_uuid: str) -> dict:
        from .proof import RuntimeProof
        proof = RuntimeProof(monitor=monitor, model_updater=model_updater, consolidation_engine=consolidation_engine, coherence_engine=coherence_engine, brain_maintenance=_brain(), relationship_engine=_relationship())
        return proof.run(session_uuid=session_uuid, allow_dream=bool((msg.args or {}).get("allow_dream", False)))

    def process_wisdom_event(msg: InboxMessage, session_uuid: str) -> dict:
        from ..wisdom.activation_engine import WisdomActivationEngine
        text = str(msg.args.get("summary") or msg.args.get("text") or "")
        if not text:
            return {"success": False, "reason": "missing summary/text"}
        return {"success": True, "report": WisdomActivationEngine().process_event(session_uuid, text, msg.args.get("source_event_id"), msg.args.get("data") or {})}

    def show_activation_trace(msg: InboxMessage, session_uuid: str) -> dict:
        from ..wisdom.activation_engine import WisdomActivationEngine
        trace_id = str(msg.args.get("trace_id") or "")
        if not trace_id:
            return {"success": False, "reason": "missing trace_id"}
        return {"success": True, "trace": WisdomActivationEngine().get_trace(trace_id)}

    def record_repair_attempt(msg: InboxMessage, session_uuid: str) -> dict:
        from ..wisdom.repair_engine import record_repair_attempt as record_repair
        result = record_repair(
            session_uuid=session_uuid,
            repair_type=str(msg.args.get("repair_type") or "clarification"),
            summary=str(msg.args.get("summary") or "Repair attempt recorded."),
            pressure_before=msg.args.get("pressure_before") or {},
            pressure_after=msg.args.get("pressure_after"),
            source_event_id=msg.args.get("source_event_id"),
            evidence_refs=msg.args.get("evidence_refs") or [],
        )
        return {"success": True, **result}

    def show_loop_signatures(msg: InboxMessage, session_uuid: str) -> dict:
        from ..wisdom.loop_detector import list_loop_signatures
        return {"success": True, "loops": list_loop_signatures(limit=int(msg.args.get("limit", 20)))}

    def run_wisdom_maintenance(msg: InboxMessage, session_uuid: str) -> dict:
        from ..wisdom.maintenance import run_wisdom_maintenance as run_maintenance
        return {"success": True, "report": run_maintenance(session_uuid)}

    def build_reasoning_context(msg: InboxMessage, session_uuid: str) -> dict:
        from ..reasoning.context_builder import build_reasoning_context as build_context
        return {"success": True, **build_context(session_uuid, msg.args.get("source_event_id"), str(msg.args.get("packet_type") or "manual"))}

    def run_reasoning_pass(msg: InboxMessage, session_uuid: str) -> dict:
        from ..reasoning.reasoning_engine import ReasoningEngine
        return ReasoningEngine().run(
            session_uuid=session_uuid,
            request_type=str(msg.args.get("request_type") or "reflection"),
            source_event_id=msg.args.get("source_event_id"),
            adapter_name=str(msg.args.get("adapter") or "mock"),
            model_name=msg.args.get("model_name"),
        )

    def show_reasoning_proposal(msg: InboxMessage, session_uuid: str) -> dict:
        from ..reasoning.proposal_store import get_proposal
        proposal_id = str(msg.args.get("proposal_id") or "")
        if not proposal_id:
            return {"success": False, "reason": "missing proposal_id"}
        return {"success": True, "proposal": get_proposal(proposal_id)}

    def list_reasoning_proposals(msg: InboxMessage, session_uuid: str) -> dict:
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT proposal_id, summary, confidence, status, created_at FROM reasoning_proposals ORDER BY id DESC LIMIT ?", (int(msg.args.get("limit", 20)),))
        return {"success": True, "proposals": [dict(row) for row in rows]}

    def run_reasoning_maintenance(msg: InboxMessage, session_uuid: str) -> dict:
        from ..reasoning.maintenance import run_reasoning_maintenance as run_maintenance
        return {"success": True, "report": run_maintenance(session_uuid)}

    def create_hypothesis(msg: InboxMessage, session_uuid: str) -> dict:
        from ..speculation import init_speculation
        text = str(msg.args.get("claim_text") or msg.args.get("text") or "")
        if not text:
            return {"success": False, "reason": "missing claim_text/text"}
        result = init_speculation().create_hypothesis(
            session_uuid=session_uuid,
            claim_text=text,
            claim_type=msg.args.get("claim_type"),
            evidence_level=str(msg.args.get("evidence_level") or "unknown"),
            confidence=float(msg.args.get("confidence", 0.3)),
            source=str(msg.args.get("source") or msg.sender or "inbox"),
            action_permission=msg.args.get("action_permission"),
        )
        return {"success": True, **result}

    def list_open_hypotheses(msg: InboxMessage, session_uuid: str) -> dict:
        from ..speculation import init_speculation
        return {"success": True, "summary": init_speculation().build_speculative_summary(session_uuid)}

    def review_hypothesis(msg: InboxMessage, session_uuid: str) -> dict:
        from ..speculation import init_speculation
        hypothesis_id = str(msg.args.get("hypothesis_id") or "")
        if not hypothesis_id:
            return {"success": False, "reason": "missing hypothesis_id"}
        return init_speculation().review_hypothesis(hypothesis_id, reviewer=msg.sender, notes=str(msg.args.get("notes") or ""))

    return {
        "status": status,
        "log_note": log_note,
        "shutdown": shutdown,
        "run_reflection": run_reflection,
        "replay_skill": replay_skill,
        "update_models": update_models,
        "run_consolidation": run_consolidation,
        "run_coherence": run_coherence,
        "run_epistemic_audit": run_epistemic_audit,
        "run_contradiction_court": run_contradiction_court,
        "run_falsification_check": run_falsification_check,
        "run_dream_pass": run_dream_pass,
        "plant_uncertainty": plant_uncertainty,
        "review_uncertainties": review_uncertainties,
        "resolve_uncertainty": resolve_uncertainty,
        "run_dignity_check": run_dignity_check,
        "run_inner_weather": run_inner_weather,
        "run_autobiography_snapshot": run_autobiography_snapshot,
        "run_brain_maintenance": run_brain_maintenance,
        "record_supervisor_interaction": record_supervisor_interaction,
        "show_supervisor_record": show_supervisor_record,
        "run_trust_review": run_trust_review,
        "list_supervisors": list_supervisors,
        "run_relationship_maintenance": run_relationship_maintenance,
        "run_runtime_proof": run_runtime_proof,
        "process_wisdom_event": process_wisdom_event,
        "show_activation_trace": show_activation_trace,
        "record_repair_attempt": record_repair_attempt,
        "show_loop_signatures": show_loop_signatures,
        "run_wisdom_maintenance": run_wisdom_maintenance,
        "build_reasoning_context": build_reasoning_context,
        "run_reasoning_pass": run_reasoning_pass,
        "show_reasoning_proposal": show_reasoning_proposal,
        "list_reasoning_proposals": list_reasoning_proposals,
        "run_reasoning_maintenance": run_reasoning_maintenance,
        "create_hypothesis": create_hypothesis,
        "list_open_hypotheses": list_open_hypotheses,
        "review_hypothesis": review_hypothesis,
    }


def register_all(
    inbox,
    loop=None,
    teaching_layer=None,
    monitor=None,
    ctx: dict | None = None,
    *,
    model_updater=None,
    consolidation_engine=None,
    coherence_engine=None,
    state_manager=None,
    brain_maintenance=None,
    relationship_engine=None,
):
    for name, handler in make_handlers(
        loop=loop,
        teaching_layer=teaching_layer,
        monitor=monitor,
        ctx=ctx,
        model_updater=model_updater,
        consolidation_engine=consolidation_engine,
        coherence_engine=coherence_engine,
        state_manager=state_manager,
        brain_maintenance=brain_maintenance,
        relationship_engine=relationship_engine,
    ).items():
        inbox.register(name, handler)
    return inbox
