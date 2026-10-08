"""Smoke tests for the host-neutral BEAN reasoning wrapper."""

import tempfile
from pathlib import Path

from bean.integration import BeanReasoningLayer
from bean.memory.store import _local, get_store


def _reset_connection():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


def test_general_reasoning_layer_mock_round_trip():
    _reset_connection()
    tmpdir = Path(tempfile.mkdtemp())

    layer = BeanReasoningLayer(str(tmpdir / "general_layer.db"))
    report = layer.observe_and_reason(
        "Host submitted an observation for analysis.",
        data={"host": "test_host", "value": 42},
        adapter_name="mock",
    )

    assert report["event_id"] > 0
    assert report["proposal_id"]
    assert report["requires_supervisor_review"] is True
    assert report["motion_command_generated"] is False
    assert report["memory_written"] is False
    assert get_store().fetchone(
        "SELECT COUNT(*) AS n FROM reasoning_proposals"
    )["n"] == 1

    layer.close()
    assert layer.closed is True


if __name__ == "__main__":
    test_general_reasoning_layer_mock_round_trip()
    print("PASS test_general_reasoning_layer_mock_round_trip")
