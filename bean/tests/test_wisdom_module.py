"""Brain 0.9 wisdom smoke tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close(); _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "wisdom.db"))
    bootstrap_identity()
    return tmpdir, begin_session()


def test_wisdom_schema_and_activation():
    _, session_uuid = make_db()
    event_id = log_event(session_uuid, EventType.HUMAN_INPUT, "Trip plan was declined due to anxiety.", Source.HUMAN, data={"stated_reason":"anxiety"})
    from bean.wisdom.activation_engine import WisdomActivationEngine
    report = WisdomActivationEngine().process_event(session_uuid, "Trip plan was declined due to anxiety.", event_id, {"stated_reason":"anxiety"})
    assert report["trace_id"]
    assert report["meaning_frame_id"]
    assert "event_fact" in report["meaning_frame"]
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM wisdom_activation_traces")["n"] == 1


def test_pressure_is_bounded():
    make_db()
    from bean.wisdom.trigger_engine import match_triggers
    from bean.wisdom.pressure_engine import compute_pressure_delta
    delta = compute_pressure_delta(match_triggers("future plan changed and is uncertain"))
    assert all(0.0 <= value <= 1.0 for value in delta.values())


def test_repair_and_loop_records():
    _, session_uuid = make_db()
    from bean.wisdom.repair_engine import record_repair_attempt
    from bean.wisdom.loop_detector import update_loop_signature
    repair = record_repair_attempt(session_uuid, "clarification", "Clarified the plan.", {"uncertainty_load":0.5}, {"uncertainty_load":0.2}, evidence_refs=[1])
    loop = update_loop_signature("uncertainty_clarification", {"trigger":"uncertainty"})
    assert repair["repair_id"]
    assert loop["loop_id"]


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name](); print(f"PASS {name}")
        except Exception:
            failed += 1; print(f"FAIL {name}"); import traceback; traceback.print_exc()
    raise SystemExit(1 if failed else 0)
