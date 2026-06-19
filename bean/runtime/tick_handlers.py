"""
bean/runtime/tick_handlers.py

Small scheduler for runtime loop handlers.
Handlers run every N ticks and errors are logged without killing the loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..memory.event_logger import log_event, EventType, Source, Severity


@dataclass
class TickHandler:
    name: str
    fn: Callable[[int, str, dict], None]
    interval: int = 1
    enabled: bool = True
    run_count: int = 0
    error_count: int = 0
    last_tick: Optional[int] = None


class TickHandlerRegistry:
    def __init__(self):
        self._handlers: list[TickHandler] = []

    def register(self, name: str, fn: Callable[[int, str, dict], None], interval: int = 1) -> TickHandler:
        if interval <= 0:
            raise ValueError("handler interval must be positive")
        handler = TickHandler(name=name, fn=fn, interval=interval)
        self._handlers.append(handler)
        return handler

    def disable(self, name: str):
        for handler in self._handlers:
            if handler.name == name:
                handler.enabled = False

    def enable(self, name: str):
        for handler in self._handlers:
            if handler.name == name:
                handler.enabled = True

    def run_due(self, tick: int, session_uuid: str, ctx: dict):
        for handler in self._handlers:
            if not handler.enabled or tick % handler.interval != 0:
                continue
            try:
                handler.fn(tick, session_uuid, ctx)
                handler.run_count += 1
                handler.last_tick = tick
            except Exception as e:
                handler.error_count += 1
                log_event(session_uuid, EventType.ERROR, f"Tick handler '{handler.name}' failed: {e}", Source.SYSTEM, subtype="tick_handler_error", severity=Severity.ERROR, data={"handler": handler.name, "tick": tick, "error": str(e)})

    def summary(self) -> list[dict]:
        return [{"name": h.name, "interval": h.interval, "enabled": h.enabled, "run_count": h.run_count, "error_count": h.error_count, "last_tick": h.last_tick} for h in self._handlers]


def build_default_handlers(
    monitor=None,
    inbox=None,
    teaching_layer=None,
    *,
    model_updater=None,
    reflection_interval: int = 300,
    monitor_interval: int = 10,
    inbox_interval: int = 1,
    model_update_interval: int = 60,
) -> TickHandlerRegistry:
    registry = TickHandlerRegistry()
    if inbox is not None:
        registry.register("inbox", lambda tick, session_uuid, ctx: inbox.poll(session_uuid), interval=inbox_interval)
    if monitor is not None:
        registry.register("system_monitor", lambda tick, session_uuid, ctx: monitor.read_and_log(session_uuid), interval=monitor_interval)
    if model_updater is not None:
        registry.register("model_update", lambda tick, session_uuid, ctx: model_updater.run(session_uuid, trigger="tick"), interval=model_update_interval)

    def scheduled_reflection(tick: int, session_uuid: str, ctx: dict):
        from ..reflection.reflect import run_reflection
        result = run_reflection(session_uuid, trigger_type="scheduled")
        log_event(session_uuid, EventType.REFLECTION, "Scheduled runtime reflection complete.", Source.SYSTEM, subtype="scheduled_reflection", data=result)
        if model_updater is not None:
            model_updater.run(session_uuid, trigger="post_reflection")

    registry.register("scheduled_reflection", scheduled_reflection, interval=reflection_interval)
    return registry
