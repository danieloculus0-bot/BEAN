"""
bean/runtime/inbox_handlers.py

Built-in handlers for file-based runtime inbox commands.
"""

from __future__ import annotations

from ..memory.event_logger import log_event, EventType, Source
from .inbox import InboxMessage


def make_handlers(loop=None, teaching_layer=None, monitor=None, ctx: dict | None = None, *, model_updater=None) -> dict:
    ctx = ctx or {}

    def status(msg: InboxMessage, session_uuid: str) -> dict:
        reading = monitor.read().to_dict() if monitor is not None else None
        loop_status = loop.status() if loop is not None else {}
        model_snapshot = model_updater.full_snapshot() if model_updater is not None else None
        return {"status": "running", "loop": loop_status, "hardware": reading, "models": model_snapshot}

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
            return {"reflection": result, "model_update": model_updater.run(session_uuid, trigger="post_reflection")}
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
        return result

    def update_models(msg: InboxMessage, session_uuid: str) -> dict:
        if model_updater is None:
            return {"success": False, "reason": "model_updater unavailable"}
        trigger = str(msg.args.get("trigger") or msg.args.get("note") or "manual")
        return {"success": True, "update": model_updater.run(session_uuid, trigger=trigger)}

    return {"status": status, "log_note": log_note, "shutdown": shutdown, "run_reflection": run_reflection, "replay_skill": replay_skill, "update_models": update_models}


def register_all(inbox, loop=None, teaching_layer=None, monitor=None, ctx: dict | None = None, *, model_updater=None):
    for name, handler in make_handlers(loop=loop, teaching_layer=teaching_layer, monitor=monitor, ctx=ctx, model_updater=model_updater).items():
        inbox.register(name, handler)
    return inbox
