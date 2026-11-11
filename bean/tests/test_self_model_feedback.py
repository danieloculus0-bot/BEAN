"""BEAN self-model: learn whether feedback was logged without pretending it was verified.

Synthetic SQLite-only evidence. No motors, devices, networks or model calls.
"""
from bean.memory.store import init_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, supersede_event, EventType, Source
from bean.world.self_model import SelfModel


POSITION = "self.uncertainty.no_sensor_feedback"
MOTION = "self.uncertainty.no_hardware_motion"


def _session(tmp_path):
    init_store(str(tmp_path / "model-feedback.db"))
    bootstrap_identity()
    return begin_session()


def _refresh(session_uuid):
    model = SelfModel()
    model.update(session_uuid)
    return model


def test_no_events_means_unknown_not_permanent_inability(tmp_path):
    session_uuid = _session(tmp_path)
    model = _refresh(session_uuid)
    for key in (POSITION, MOTION):
        claim = model.get(key)
        assert claim.parsed_value() == {
            "status": "not_recorded",
            "last_event_id": None,
            "independently_verified": False,
        }
        assert "not" in claim.content.lower() or "unverified" in claim.content.lower()
        assert not claim.evidence


def test_camera_simulation_and_self_report_are_not_joint_feedback(tmp_path):
    session_uuid = _session(tmp_path)
    log_event(session_uuid, EventType.SENSOR_READING, "Camera frame", Source.SENSOR, subtype="camera_frame")
    log_event(session_uuid, EventType.BODY_STATE, "Simulated body movement", Source.SYSTEM,
              data={"joint_position": 45, "simulated": True})
    log_event(session_uuid, EventType.SENSOR_READING, "Claimed position", Source.LLM,
              subtype="joint_position_feedback")
    log_event(session_uuid, EventType.SENSOR_READING, "Claimed motion", Source.SYSTEM,
              subtype="physical_motion_feedback")
    model = _refresh(session_uuid)
    assert model.get_value(POSITION)["status"] == "not_recorded"
    assert model.get_value(MOTION)["status"] == "not_recorded"


def test_reported_feedback_revises_claim_without_claiming_physical_truth(tmp_path):
    session_uuid = _session(tmp_path)
    model = _refresh(session_uuid)
    first = model.get(POSITION)
    reading_id = log_event(session_uuid, EventType.SENSOR_READING,
                           "Synthetic position feedback", Source.SENSOR,
                           subtype="joint_position_feedback", data={"joint": "test_joint", "position": 10})
    model.update(session_uuid)
    claim = model.get(POSITION)
    assert claim.parsed_value() == {
        "status": "reported_unverified",
        "last_event_id": reading_id,
        "independently_verified": False,
    }
    assert claim.source_ref and claim.source_ref.startswith("event:")
    assert claim.evidence == [claim.source_ref]
    assert "accuracy remains unverified" in claim.content
    assert not first.active or len(model._store.get_history(POSITION)) >= 2
    assert model.get_value(MOTION)["status"] == "not_recorded"


def test_motion_requires_explicit_sensor_sourced_motion_event(tmp_path):
    session_uuid = _session(tmp_path)
    log_event(session_uuid, EventType.SENSOR_READING, "Joint reading", Source.SENSOR,
              subtype="joint_position_feedback")
    model = _refresh(session_uuid)
    assert model.get_value(MOTION)["status"] == "not_recorded"
    motion_id = log_event(session_uuid, EventType.SENSOR_READING, "Sensor-reported motion",
                          Source.SENSOR, subtype="physical_motion_feedback")
    model.update(session_uuid)
    assert model.get_value(MOTION)["last_event_id"] == motion_id
    assert model.get_value(MOTION)["independently_verified"] is False
    assert "independent confirmation" in model.get(MOTION).content.lower()


def test_correction_retracts_stale_sensor_claim_but_preserves_history(tmp_path):
    session_uuid = _session(tmp_path)
    first = log_event(session_uuid, EventType.SENSOR_READING, "Incorrect feedback",
                      Source.SENSOR, subtype="joint_position_feedback")
    model = _refresh(session_uuid)
    assert model.get_value(POSITION)["status"] == "reported_unverified"
    replacement = log_event(session_uuid, EventType.WARNING, "Correction: no valid joint reading",
                            Source.SYSTEM, subtype="feedback_retraction")
    supersede_event(first, replacement)
    model.update(session_uuid)
    assert model.get_value(POSITION)["status"] == "not_recorded"
    history = model._store.get_history(POSITION)
    assert len(history) == 2
    assert history[0].parsed_value()["status"] == "reported_unverified"
    assert history[0].active is False
    assert history[1].parsed_value()["status"] == "not_recorded"


def test_recorded_feedback_survives_fresh_process_database_reopen(tmp_path):
    path = tmp_path / "model-feedback.db"
    session_uuid = _session(tmp_path)
    logged_id = log_event(session_uuid, EventType.SENSOR_READING,
                          "Synthetic persisted feedback", Source.SENSOR,
                          subtype="joint_position_feedback")
    assert _refresh(session_uuid).get_value(POSITION)["last_event_id"] == logged_id
    init_store(str(path))
    fresh_session_uuid = begin_session()
    assert _refresh(fresh_session_uuid).get_value(POSITION)["last_event_id"] == logged_id
