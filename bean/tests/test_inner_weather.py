"""Smoke tests for Inner Weather."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source, Severity
from bean.cognition.inner_weather import InnerWeatherEngine


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "inner_weather_test.db"))
    bootstrap_identity()
    return begin_session()


def test_inner_weather_reports_pressure_not_emotion():
    session_uuid = make_db()
    log_event(session_uuid, EventType.WARNING, "test warning", Source.SYSTEM, severity=Severity.WARN)
    report = InnerWeatherEngine().generate(session_uuid)
    assert report.risk_pressure > 0
    assert "risk=" in report.summary
    assert "feel" not in report.summary.lower()


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
