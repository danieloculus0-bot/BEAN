"""Smoke tests for BEAN Brain 0.3 falsification engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.cognition.falsification import FalsificationEngine, FalsificationRule, FalsificationType


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "falsification_test.db"))
    bootstrap_identity()
    return begin_session()


def test_missing_recent_event_falsifies_claim():
    make_db()
    engine = FalsificationEngine()
    engine.add_missing_recent_event_rule(
        claim_key="audio.input.working",
        event_type="sensor_reading",
        subtype="audio_heartbeat",
        max_age_minutes=5,
    )
    results = engine.check_all()
    assert len(results) == 1
    assert results[0].falsified is True
    assert results[0].action_taken == "downgrade_to_uncertain"


def test_recent_event_keeps_claim_alive():
    session_uuid = make_db()
    log_event(session_uuid, EventType.SENSOR_READING, "Audio heartbeat observed.", Source.SENSOR, subtype="audio_heartbeat")
    engine = FalsificationEngine()
    engine.add_missing_recent_event_rule(
        claim_key="audio.input.working",
        event_type="sensor_reading",
        subtype="audio_heartbeat",
        max_age_minutes=5,
    )
    results = engine.check_all()
    assert results[0].falsified is False
    assert results[0].action_taken == "none"


def test_sql_assertion_rule_records_result():
    make_db()
    engine = FalsificationEngine()
    rule = FalsificationRule(
        claim_key="identity.exists",
        falsification_type=FalsificationType.SQL_ASSERTION_FALSE,
        condition={},
        check_query="SELECT COUNT(*) FROM identity WHERE id=1",
        failure_action="rebootstrap_identity",
    )
    engine.add_rule(rule)
    result = engine.check_all()[0]
    assert result.falsified is False
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM claim_falsification_results")["n"] == 1


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
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
