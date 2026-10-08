"""Host-neutral deployment wrapper for BEAN's reasoning layer.

This module intentionally stops at proposals. The host application remains
responsible for permissions, actions, actuators, workflow changes, and other
side effects.
"""

from __future__ import annotations

from typing import Any

from bean.memory.event_logger import EventType, Severity, Source, log_event
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session, end_session
from bean.memory.store import init_store
from bean.reasoning import ReasoningEngine


class BeanReasoningLayer:
    """Thin lifecycle and reasoning wrapper for one host process."""

    def __init__(
        self,
        db_path: str,
        *,
        adapter=None,
        bootstrap_declared_state: bool = True,
    ):
        self.store = init_store(db_path)
        if bootstrap_declared_state:
            bootstrap_identity()
        self.session_uuid = begin_session()
        self.engine = ReasoningEngine(adapter=adapter)
        self.closed = False

    def _ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("BEAN reasoning layer is closed")

    def record_event(
        self,
        summary: str,
        *,
        event_type: EventType = EventType.OBSERVATION,
        source: Source = Source.SYSTEM,
        subtype: str | None = None,
        data: dict[str, Any] | None = None,
        severity: Severity = Severity.INFO,
    ) -> int:
        """Record a canonical BEAN event and return its row ID."""
        self._ensure_open()
        return log_event(
            session_uuid=self.session_uuid,
            event_type=event_type,
            summary=summary,
            source=source,
            subtype=subtype,
            data=data,
            severity=severity,
        )

    def reason(
        self,
        *,
        request_type: str = "analysis",
        source_event_id: int | None = None,
        adapter_name: str = "mock",
        model_name: str | None = None,
    ) -> dict:
        """Create and store a reasoning proposal. This method never acts."""
        self._ensure_open()
        return self.engine.run(
            session_uuid=self.session_uuid,
            request_type=request_type,
            source_event_id=source_event_id,
            adapter_name=adapter_name,
            model_name=model_name,
        )

    def observe_and_reason(
        self,
        summary: str,
        *,
        data: dict[str, Any] | None = None,
        subtype: str | None = None,
        request_type: str = "analysis",
        adapter_name: str = "mock",
        model_name: str | None = None,
        source: Source = Source.SYSTEM,
        severity: Severity = Severity.INFO,
    ) -> dict:
        """Record an observation, reason over it, and return trace IDs."""
        event_id = self.record_event(
            summary,
            event_type=EventType.OBSERVATION,
            source=source,
            subtype=subtype,
            data=data,
            severity=severity,
        )
        result = self.reason(
            request_type=request_type,
            source_event_id=event_id,
            adapter_name=adapter_name,
            model_name=model_name,
        )
        return {"event_id": event_id, **result}

    def close(self, reason: str = "clean", notes: str | None = None) -> None:
        if self.closed:
            return
        end_session(self.session_uuid, reason=reason, notes=notes)
        self.store.close()
        self.closed = True

    def __enter__(self) -> "BeanReasoningLayer":
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        if exc is None:
            self.close()
        else:
            self.close(reason="error", notes=str(exc))
        return False
