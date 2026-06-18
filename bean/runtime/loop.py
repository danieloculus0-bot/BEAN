"""
bean/runtime/loop.py

Main BEAN runtime tick loop.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Optional

from ..memory.event_logger import log_event, EventType, Source, Severity
from .tick_handlers import TickHandlerRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BeanLoop:
    def __init__(self, ctx: dict, handlers: TickHandlerRegistry, tick_rate_hz: float = 1.0, max_ticks: Optional[int] = None):
        if tick_rate_hz <= 0:
            raise ValueError(f"tick_rate_hz must be positive, got {tick_rate_hz}")
        self._ctx = ctx
        self._session_uuid = ctx["session_uuid"]
        self._handlers = handlers
        self._tick_interval = 1.0 / tick_rate_hz
        self._max_ticks = max_ticks
        self._tick = 0
        self._running = False
        self._shutdown_requested = False
        self._shutdown_reason = "clean"
        self._shutdown_lock = threading.Lock()
        self._started_at: Optional[str] = None
        self._stopped_at: Optional[str] = None
        ctx["loop"] = self

    def request_shutdown(self, reason: str = "clean"):
        with self._shutdown_lock:
            if not self._shutdown_requested:
                self._shutdown_requested = True
                self._shutdown_reason = reason
                self._ctx["_shutdown_called"] = True

    def run(self):
        self._running = True
        self._started_at = _now()
        log_event(self._session_uuid, EventType.SESSION_START, f"Runtime loop started at {1.0 / self._tick_interval:.2f} Hz.", Source.SYSTEM, data={"max_ticks": self._max_ticks, "handlers": self._handlers.summary()})
        try:
            while True:
                with self._shutdown_lock:
                    if self._shutdown_requested:
                        break
                if self._max_ticks is not None and self._tick >= self._max_ticks:
                    self._shutdown_reason = "max_ticks_reached"
                    break
                start = time.monotonic()
                self._handlers.run_due(self._tick, self._session_uuid, self._ctx)
                self._tick += 1
                sleep_for = self._tick_interval - (time.monotonic() - start)
                if sleep_for > 0:
                    time.sleep(sleep_for)
        finally:
            self._running = False
            self._stopped_at = _now()
            self._post_session()

    def _post_session(self):
        try:
            from ..reflection.reflect import run_reflection
            reflection = run_reflection(self._session_uuid, trigger_type="post_session")
        except Exception as e:
            reflection = {"error": str(e)}
            log_event(self._session_uuid, EventType.ERROR, f"Post-session reflection failed: {e}", Source.SYSTEM, subtype="post_session_error", severity=Severity.ERROR, data=reflection)
        log_event(
            self._session_uuid,
            EventType.SESSION_END,
            f"Runtime loop ended after {self._tick} tick(s). Reason: {self._shutdown_reason}.",
            Source.SYSTEM,
            data={"tick_count": self._tick, "shutdown_reason": self._shutdown_reason, "started_at": self._started_at, "stopped_at": self._stopped_at, "handlers": self._handlers.summary(), "reflection": reflection},
        )

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def running(self) -> bool:
        return self._running

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def status(self) -> dict:
        return {"running": self._running, "tick": self._tick, "shutdown_requested": self._shutdown_requested, "shutdown_reason": self._shutdown_reason, "started_at": self._started_at, "stopped_at": self._stopped_at, "handlers": self._handlers.summary()}
