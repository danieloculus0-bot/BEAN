"""Host-neutral BEAN adapter: explicit proposal-only contract and lifecycle."""
from pathlib import Path

import pytest

from bean.integration import BeanReasoningLayer
from bean.memory.store import get_store


def test_host_adapter_records_evidence_without_executing(tmp_path):
    path = str(tmp_path / "host.db")
    with BeanReasoningLayer(path) as layer:
        event_id = layer.record_event("First measured condition", data={"value": 0})
        result = layer.reason(source_event_id=event_id, adapter_name="mock")
        assert result["proposal_id"]
        assert result["requires_supervisor_review"] is True
        assert result["motion_command_generated"] is False
        assert result["memory_written"] is False
        assert result["filter_passed"] in (True, False)
        assert get_store().fetchone(
            "SELECT COUNT(*) AS n FROM events WHERE id=?", (event_id,)
        )["n"] == 1
    with pytest.raises(RuntimeError, match="closed"):
        layer.reason(adapter_name="mock")


def test_sequential_host_databases_do_not_share_event_history(tmp_path):
    first = str(tmp_path / "host_a.db")
    second = str(tmp_path / "host_b.db")
    with BeanReasoningLayer(first) as a:
        id_a = a.record_event("Only host A can see this", data={"host": "a"})
        assert id_a > 0
    with BeanReasoningLayer(second) as b:
        events = get_store().fetchall(
            "SELECT summary FROM events WHERE summary=?", ("Only host A can see this",)
        )
        assert events == []
        assert b.observe_and_reason("Only host B can see this", adapter_name="mock")["proposal_id"]
    assert Path(first).exists() and Path(second).exists()


def test_context_manager_records_failed_session_but_does_not_swallow_error(tmp_path):
    with pytest.raises(ValueError, match="test failure"):
        with BeanReasoningLayer(str(tmp_path / "failure.db")) as layer:
            layer.record_event("Pre-error observation")
            raise ValueError("test failure")
    assert layer.closed is True
