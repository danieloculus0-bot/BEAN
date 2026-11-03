"""Synthetic append-only correction checks, without any real-world records."""
import json
from uuid import uuid4

import pytest

from bean.memory.audit_mirror import mirror_path
from bean.memory.event_logger import EventType, Source, log_event
from bean.memory.receipt_contract import make_receipt_data, receipt_from_event
from bean.memory.receipt_correction import correction_data_for_event
from bean.memory.store import get_store, init_store


def _original():
    return make_receipt_data(
        request_id=str(uuid4()), correlation_id=str(uuid4()),
        module="fictional.scheduler", action="reserve_slot",
        outcome="unknown", evidence_refs=["journal:fictional-a"],
        uncertainty=0.8, metadata={"synthetic": True},
    )


def test_append_only_correction_roundtrip_restart_and_mirror(tmp_path):
    db = tmp_path / "fictional.sqlite"
    init_store(str(db))
    first_id = log_event("fictional-session", EventType.OBSERVATION,
                         "Fictional observation", Source.SYSTEM, data=_original())
    first_row = dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (first_id,)))
    original = receipt_from_event(first_row)
    mirror_before = mirror_path(db).read_bytes()
    correction_data = correction_data_for_event(
        target_event_id=original["event_id"], request_id=str(uuid4()),
        outcome="failed", evidence_refs=["journal:fictional-review"],
        uncertainty=0.1, metadata={"synthetic": True},
    )
    assert dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (first_id,))) == first_row
    assert mirror_path(db).read_bytes() == mirror_before
    second_id = log_event("fictional-session", EventType.OBSERVATION,
                          "Fictional correction", Source.SYSTEM, data=correction_data)
    second = receipt_from_event(get_store().fetchone("SELECT * FROM events WHERE id=?", (second_id,)))
    assert second["event_id"] != original["event_id"]
    assert second["request_id"] != original["request_id"]
    assert second["correlation_id"] == original["correlation_id"]
    assert second["module"] == original["module"]
    assert second["relations"][0]["kind"] == "corrects"
    assert second["relations"][0]["target_event_id"] == original["event_id"]
    assert dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (first_id,))) == first_row
    mirror_after = mirror_path(db).read_bytes()
    mirrored = [json.loads(line) for line in mirror_after.splitlines()]
    assert len(mirrored) == 2
    assert receipt_from_event(mirrored[0]) == original
    assert receipt_from_event(mirrored[1]) == second
    init_store(str(db))
    assert mirror_path(db).read_bytes() == mirror_after
    assert dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (first_id,))) == first_row
    assert receipt_from_event(get_store().fetchone("SELECT * FROM events WHERE id=?", (second_id,))) == second


def test_missing_and_legacy_targets_are_not_invented(tmp_path):
    init_store(str(tmp_path / "fictional.sqlite"))
    with pytest.raises(ValueError, match="not a persisted"):
        correction_data_for_event(target_event_id=str(uuid4()), request_id=str(uuid4()),
                                  outcome="failed", evidence_refs=["journal:fictional"])
    legacy_id = log_event("fictional-session", EventType.OBSERVATION,
                          "Fictional legacy", Source.SYSTEM, data={"legacy": True})
    legacy_uuid = get_store().fetchone("SELECT event_uuid FROM events WHERE id=?", (legacy_id,))["event_uuid"]
    with pytest.raises(ValueError, match="no v1 receipt"):
        correction_data_for_event(target_event_id=legacy_uuid, request_id=str(uuid4()),
                                  outcome="failed", evidence_refs=["journal:fictional"])


def test_correction_rejects_unsupported_evidence_and_private_payload(tmp_path):
    init_store(str(tmp_path / "fictional.sqlite"))
    first = log_event("fictional-session", EventType.OBSERVATION,
                      "Fictional observation", Source.SYSTEM, data=_original())
    event_uuid = get_store().fetchone("SELECT event_uuid FROM events WHERE id=?", (first,))["event_uuid"]
    base = dict(target_event_id=event_uuid, request_id=str(uuid4()), outcome="failed")
    with pytest.raises(ValueError, match="non-event evidence"):
        correction_data_for_event(**base, evidence_refs=["event:" + event_uuid])
    with pytest.raises(ValueError, match="opaque"):
        correction_data_for_event(**base, evidence_refs=["/private/file.txt"])
    with pytest.raises(ValueError, match="privacy"):
        correction_data_for_event(**base, evidence_refs=["journal:fictional"],
                                  metadata={"private_note": "not allowed"})
    with pytest.raises(ValueError, match="uncertainty"):
        correction_data_for_event(**base, evidence_refs=["journal:fictional"],
                                  uncertainty=float("nan"))
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"] == 1
