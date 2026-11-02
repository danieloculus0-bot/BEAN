"""Fictional, model-free read-only receipt preview regression tests."""
import json
from uuid import uuid4

import pytest

from bean.memory.audit_mirror import mirror_path
from bean.memory.event_logger import EventType, Source, log_event
from bean.memory.receipt_contract import make_receipt_data
from bean.memory.receipt_preview import recent_receipt_preview
from bean.memory.store import get_store, init_store


def _receipt(correlation, **changes):
    fields = dict(request_id=str(uuid4()), correlation_id=correlation,
                  module="fictional.scheduler", action="reserve_slot",
                  outcome="failed", evidence_refs=["journal:fictional-001"],
                  uncertainty=0.4, metadata={"synthetic": True})
    fields.update(changes)
    return make_receipt_data(**fields)


def test_explicit_cross_module_relation_and_no_private_echo(tmp_path):
    db = tmp_path / "fictional.sqlite"
    init_store(str(db))
    correlation = str(uuid4())
    first_id = log_event("fictional", EventType.OBSERVATION,
                         "Private free text must not be echoed", Source.SYSTEM,
                         data=_receipt(correlation))
    first_uuid = get_store().fetchone(
        "SELECT event_uuid FROM events WHERE id=?", (first_id,)
    )["event_uuid"]
    relation = {"kind": "resembles", "target_event_id": first_uuid,
                "evidence_refs": ["event:" + first_uuid], "uncertainty": 0.7}
    log_event("fictional", EventType.OBSERVATION, "Another private summary",
              Source.SYSTEM, data=_receipt(
                  correlation, module="fictional.maintenance",
                  action="inspect_fixture", outcome="unknown",
                  relations=[relation]))
    log_event("fictional", EventType.OBSERVATION,
              "Legacy private details", Source.SYSTEM, data={"private": "do not echo"})
    before = mirror_path(db).read_bytes()
    preview = recent_receipt_preview(
        limit=10, scan_limit=20, correlation_id=correlation,
        related_to_event_id=first_uuid
    )
    assert preview["schema"] == "bean.receipt_preview.v1"
    assert preview["read_only"] is True
    assert preview["status"] == "observed"
    assert preview["scanned"] == 3
    assert preview["skipped_legacy_or_invalid"] == 1
    assert len(preview["receipts"]) == 1
    item = preview["receipts"][0]
    assert item["module"] == "fictional.maintenance"
    assert item["outcome"] == "unknown"
    assert item["relations"][0]["kind"] == "resembles"
    assert item["relations"][0]["target_event_id"] == first_uuid
    assert "summary" not in item and "data" not in item
    assert "private" not in json.dumps(preview).lower()
    assert mirror_path(db).read_bytes() == before
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"] == 3


def test_preview_restart_replay_is_stable(tmp_path):
    db = tmp_path / "fictional.sqlite"
    init_store(str(db))
    correlation = str(uuid4())
    log_event("fictional", EventType.OBSERVATION, "Fictional attempt",
              Source.SYSTEM, data=_receipt(correlation))
    before = recent_receipt_preview(limit=5)
    mirror_before = mirror_path(db).read_bytes()
    init_store(str(db))
    after = recent_receipt_preview(limit=5)
    assert before == after
    assert mirror_path(db).read_bytes() == mirror_before
    assert recent_receipt_preview(
        correlation_id=str(uuid4())
    )["status"] == "no_matches_in_window"


def test_preview_bounded_and_rejects_invalid_filters(tmp_path):
    db = tmp_path / "fictional.sqlite"
    init_store(str(db))
    correlation = str(uuid4())
    log_event("fictional", EventType.OBSERVATION, "Older fictional",
              Source.SYSTEM, data=_receipt(correlation))
    log_event("fictional", EventType.OBSERVATION, "Newer legacy",
              Source.SYSTEM, data={"legacy": True})
    bounded = recent_receipt_preview(limit=1, scan_limit=1)
    assert bounded["receipts"] == []
    assert bounded["scan_limit_reached"] is True
    assert bounded["skipped_legacy_or_invalid"] == 1
    assert recent_receipt_preview(limit=1, scan_limit=2)["receipts"][0]["outcome"] == "failed"
    for options in ({"limit": True}, {"limit": 51},
                    {"limit": 3, "scan_limit": 2},
                    {"correlation_id": "not-a-uuid"},
                    {"related_to_event_id": "not-a-uuid"}):
        with pytest.raises(ValueError):
            recent_receipt_preview(**options)
