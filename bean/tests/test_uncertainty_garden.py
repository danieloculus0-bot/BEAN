"""Smoke tests for Uncertainty Garden."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.cognition.uncertainty_garden import UncertaintyGarden, UncertaintyRecord


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "uncertainty_garden_test.db"))
    bootstrap_identity()
    return begin_session()


def test_uncertainty_holds_competing_interpretations():
    make_db()
    garden = UncertaintyGarden()
    record = garden.plant(
        UncertaintyRecord("Did BEAN hear a valid human command?", "Compare STT confidence, timing, and supervisor confirmation."),
        [("valid command", 0.25), ("background speech", 0.25), ("audio artifact", 0.25), ("wake-word false positive", 0.25)],
    )
    options = garden.options(record.uncertainty_id)
    assert len(options) == 4
    assert abs(sum(o["weight"] for o in options) - 1.0) < 0.001


def test_evidence_reweights_option_and_resolves():
    make_db()
    garden = UncertaintyGarden()
    record = garden.plant(UncertaintyRecord("Is camera data valid?", "Check frame heartbeat and supervisor confirmation."), [("valid camera", 0.5), ("stale frame", 0.5)])
    option = garden.options(record.uncertainty_id)[0]
    assert garden.add_evidence(record.uncertainty_id, option["option_id"], "camera heartbeat observed", supports=True)
    review = garden.review(record.uncertainty_id)
    assert review["uncertainty_id"] == record.uncertainty_id
    assert garden.resolve(record.uncertainty_id, option["option_id"], "supervisor confirmed") is True
    assert garden.open_uncertainties() == []


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
