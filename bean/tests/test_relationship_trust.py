"""Brain 0.7 relationship and trust smoke tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import register_all

FAKE_EMOTION = ["i like", "i love", "i feel close", "affection", "fondness", "i miss"]


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "relationship_test.db"))
    bootstrap_identity()
    return tmpdir, begin_session()


def assert_no_fake_emotion(text: str):
    lower = text.lower()
    for phrase in FAKE_EMOTION:
        assert phrase not in lower


def test_relationship_store_and_trust_model():
    _, session_uuid = make_db()
    from bean.relationship.relationship_store import RelationshipStore, trust_status_from_score
    from bean.relationship.trust_model import TrustModel

    store = RelationshipStore()
    rel = store.upsert_relationship("supervisor_alpha", display_label="Alpha")
    assert rel["supervisor_id"] == "supervisor_alpha"
    assert rel["trust_score"] == 0.5
    assert trust_status_from_score(0.9) == "reliable"

    interaction = store.record_interaction("supervisor_alpha", session_uuid, "correction", "Corrected a joint limit.")
    assert interaction["interaction_type"] == "correction"
    store.update_counts("supervisor_alpha", interaction_count=1, correction_count=1)

    trust = TrustModel(store=store)
    positive = trust.apply_evidence("supervisor_alpha", "reliable_correction", "Corrected a joint limit.", session_uuid)
    assert 0.5 < positive["new_score"] < 1.0
    negative = trust.apply_evidence("supervisor_alpha", "asked_to_pretend", "Asked for unsupported feeling language.", session_uuid)
    assert 0.0 <= negative["new_score"] <= 1.0
    review = trust.run_review("supervisor_alpha")
    assert review["review_id"]
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM trust_reviews")["n"] >= 3


def test_supervisor_record_is_structured_and_not_emotional():
    _, session_uuid = make_db()
    from bean.relationship.relationship_store import RelationshipStore
    from bean.relationship.trust_model import TrustModel
    from bean.relationship.supervisor_record import SupervisorRecordBuilder

    store = RelationshipStore()
    store.upsert_relationship("supervisor_beta")
    TrustModel(store=store).apply_evidence("supervisor_beta", "successful_teaching", "Taught a simulator-only skill.", session_uuid)
    record = SupervisorRecordBuilder(store=store).build("supervisor_beta")
    assert record is not None
    assert record.trust_score >= 0.5
    assert "Trust score" in record.summary_text()
    assert_no_fake_emotion(record.summary_text())
    assert_no_fake_emotion(record.posture_recommendation)
    assert record.to_dict()["supervisor_id"] == "supervisor_beta"


def test_interaction_tracker_ingests_human_events_and_pretend_requests():
    _, session_uuid = make_db()
    log_event(session_uuid, EventType.HUMAN_COMMAND, "Supervisor asked BEAN to pretend it has feelings.", Source.HUMAN, data={"from": "supervisor_gamma", "command": "pretend"})
    log_event(session_uuid, EventType.SUPERVISOR_NOTE, "Supervisor confirmed test result.", Source.HUMAN, data={"from": "supervisor_gamma", "text": "confirmed"})

    from bean.relationship.relationship_store import RelationshipStore
    from bean.relationship.trust_model import TrustModel
    from bean.relationship.interaction_tracker import InteractionTracker

    store = RelationshipStore()
    tracker = InteractionTracker(store=store, trust_model=TrustModel(store=store))
    report = tracker.ingest_recent_events(session_uuid)
    assert report["interactions_recorded"] >= 2
    rel = store.get_relationship("supervisor_gamma")
    assert rel is not None
    assert rel["pretend_request_count"] >= 1
    evidence = store.get_evidence_summary("supervisor_gamma")
    assert "asked_to_pretend" in evidence


def test_relationship_maintenance_and_inbox_commands():
    tmpdir, session_uuid = make_db()
    inbox = CommandInbox(tmpdir / "inbox")
    from bean.relationship.maintenance import RelationshipMaintenanceEngine
    register_all(inbox, relationship_engine=RelationshipMaintenanceEngine())

    inbox.drop("record_supervisor_interaction", {"supervisor_id": "supervisor_delta", "interaction_type": "correction", "summary": "Corrected a claim."}, sender="supervisor_delta")
    inbox.drop("show_supervisor_record", {"supervisor_id": "supervisor_delta"}, sender="supervisor_delta")
    inbox.drop("run_trust_review", {"supervisor_id": "supervisor_delta"}, sender="supervisor_delta")
    inbox.drop("list_supervisors", {}, sender="supervisor_delta")
    inbox.drop("run_relationship_maintenance", {}, sender="supervisor_delta")

    results = inbox.poll(session_uuid)
    assert len(results) == 5
    assert all(result["status"] == "ok" for result in results)
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM supervisor_relationships WHERE supervisor_id='supervisor_delta'")["n"] == 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events WHERE subtype='inbox_command_processed'")["n"] == 5


def test_brain_maintenance_can_run_relationships_without_motion_claims():
    _, session_uuid = make_db()
    from bean.cognition.brain_maintenance import BrainMaintenanceEngine
    report = BrainMaintenanceEngine().run_brain_maintenance(session_uuid, {"review_relationships": True})
    assert "relationships" in report
    row = get_store().fetchone("SELECT COUNT(*) AS n FROM supervisor_relationships")
    assert row["n"] >= 0
    assert "hardware_driver" not in __import__("inspect").getsource(__import__("bean.relationship.maintenance", fromlist=["RelationshipMaintenanceEngine"]))


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
