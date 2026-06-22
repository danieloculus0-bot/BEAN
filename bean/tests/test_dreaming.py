"""Smoke tests for Dream Engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.cognition.dreaming import DreamEngine, DreamType


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "dreaming_test.db"))
    bootstrap_identity()
    return begin_session()


def test_dream_is_synthetic_not_observed_memory():
    session_uuid = make_db()
    log_event(session_uuid, EventType.SENSOR_READING, "Camera heartbeat.", Source.SENSOR, subtype="camera")
    dream = DreamEngine().run_pass(session_uuid, DreamType.COMPRESSION)
    assert dream.not_real_event is True
    assert dream.not_observed is True
    row = get_store().fetchone("SELECT * FROM dream_records WHERE dream_id=?", (dream.dream_id,))
    assert row is not None
    assert row["not_real_event"] == 1


def test_curiosity_dream_references_open_questions():
    session_uuid = make_db()
    get_store().execute("INSERT INTO curiosity (question, context, status) VALUES (?, ?, 'open')", ("What caused the audio uncertainty?", "test"))
    get_store().commit()
    dream = DreamEngine().run_pass(session_uuid, DreamType.CURIOSITY)
    assert "audio uncertainty" in dream.content


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    passed = failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
            passed += 1
        except Exception:
            print(f"FAIL {name}")
            import traceback; traceback.print_exc()
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
