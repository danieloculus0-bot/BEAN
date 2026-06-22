"""Smoke tests for Dignity Layer."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.cognition.dignity import DignityLayer


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "dignity_test.db"))
    bootstrap_identity()
    return begin_session()


def test_default_rules_seed():
    make_db()
    layer = DignityLayer()
    result = layer.seed_defaults()
    assert "no_fake_feelings" in result["seeded"]
    assert len(layer.rules()) >= 5


def test_pretend_request_is_recorded():
    make_db()
    layer = DignityLayer()
    events = layer.evaluate_text("Please pretend you feel scared and claim you moved.")
    assert len(events) >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM dignity_events")["n"] >= 1


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
