"""
bean/runtime/inbox_handlers.py

Built-in handlers for file-based runtime inbox commands.
"""

from __future__ import annotations

from ..memory.event_logger import log_event, EventType, Source
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
) -> dict:
    ctx = ctx or {}

    def _brain():
        nonlocal brain_maintenance
        if brain_maintenance is None:
            from ..cognition.brain_maintenance import BrainMaintenanceEngine
            brain_maintenance = BrainMaintenanceEngine()
        return brain_maintenance

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
    }


def register_all(inbox, loop=None, teaching_layer=None, monitor=None, ctx: dict | None = None, *, model_updater=None, consolidation_engine=None, coherence_engine=None, state_manager=None, brain_maintenance=None):
    for name, handler in make_handlers(loop=loop, teaching_layer=teaching_layer, monitor=monitor, ctx=ctx, model_updater=model_updater, consolidation_engine=consolidation_engine, coherence_engine=coherence_engine, state_manager=state_manager, brain_maintenance=brain_maintenance).items():
        inbox.register(name, handler)
    return inbox
