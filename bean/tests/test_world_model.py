"""
Compact tests for BEAN world/self model layer.
"""

import json
import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.world.claim import ClaimCategory, ClaimSource, make_claim
from bean.world.model_store import ModelStore
from bean.world.self_model import SelfModel
from bean.world.world_model import WorldModel
from bean.world.updater import ModelUpdater


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = tempfile.mkdtemp()
    init_store(str(Path(tmpdir) / "world_model_test.db"))
    bootstrap_identity()
    return begin_session()


def test_claim_store_supersedes_by_key():
    make_db()
    store = ModelStore()
    first = make_claim("self.test", "old", ClaimCategory.SELF, ClaimSource.BOOTSTRAP, 1.0)
    second = make_claim("self.test", "new", ClaimCategory.SELF, ClaimSource.EVENT_LOG, 0.8)
    store.save(first)
    store.save(second)
    assert store.get_active("self.test").content == "new"
    hist = store.get_history("self.test")
    assert len(hist) == 2
    assert hist[0].active is False


def test_self_model_derives_identity_and_history():
    session_uuid = make_db()
    updater = ModelUpdater()
    result = updater.run(session_uuid, trigger="test")
    assert result["self_claims_derived"] > 0
    snap = updater.full_snapshot()
    assert "self.identity.name" in snap["self_model"]["claims"]
    assert "self.history.total_events" in snap["self_model"]["claims"]


def test_world_model_records_uncertainties():
    session_uuid = make_db()
    updater = ModelUpdater()
    updater.run(session_uuid, trigger="test")
    keys = {c["key"] for c in updater.full_snapshot()["uncertainties"]}
    assert "environment.uncertainty.no_spatial_map" in keys
    assert "environment.uncertainty.no_vision" in keys


def test_world_model_supervisor_claim_logs_event():
    session_uuid = make_db()
    store = ModelStore()
    world = WorldModel(store=store)
    world.add_supervisor_claim("environment.space.description", "The robot is in the office.", session_uuid, value={"room": "office"})
    claim = store.get_active("environment.space.description")
    assert claim is not None
    assert claim.parsed_value()["room"] == "office"
    row = get_store().fetchone("SELECT * FROM events WHERE subtype='supervisor_claim'")
    assert row is not None


def test_model_updater_snapshot_is_json_serializable():
    session_uuid = make_db()
    log_event(session_uuid, EventType.SENSOR_READING, "Camera test event", Source.SENSOR, subtype="camera")
    updater = ModelUpdater()
    updater.run(session_uuid, trigger="test")
    json.dumps(updater.full_snapshot())


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
            failed += 1
            import traceback; traceback.print_exc()
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
