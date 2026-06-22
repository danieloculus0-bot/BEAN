"""Smoke tests for Autobiography Engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.cognition.dreaming import DreamEngine, DreamType
from bean.cognition.autobiography import AutobiographyEngine


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "autobiography_test.db"))
    bootstrap_identity()
    return begin_session()


def test_autobiography_builds_timeline_entries():
    session_uuid = make_db()
    DreamEngine().run_pass(session_uuid, DreamType.IDENTITY)
    engine = AutobiographyEngine()
    entries = engine.build_snapshot(session_uuid)
    assert entries
    timeline = engine.timeline()
    assert timeline
    assert any(e["entry_type"] == "summary" for e in timeline)
    assert any(e["entry_type"] == "dream" for e in timeline)


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
