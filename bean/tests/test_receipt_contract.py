"""Fully fictional cross-module receipt tests, no hardware or provider calls."""
import json
from uuid import uuid4

import pytest

from bean.memory.receipt_contract import make_receipt_data, receipt_from_event
from bean.memory.audit_mirror import mirror_path
from bean.memory.event_logger import EventType, Source, log_event
from bean.memory.store import get_store, init_store


def _args(**overrides):
    values = dict(request_id=str(uuid4()), correlation_id=str(uuid4()),
                  module="fictional.scheduler", action="reserve_slot",
                  outcome="failed", evidence_refs=["journal:synthetic-test-01"],
                  uncertainty=0.25, metadata={"synthetic": True, "attempt": 1})
    values.update(overrides)
    return values


def test_canonical_event_roundtrip_and_restart_replay(tmp_path):
    db = tmp_path / "synthetic.sqlite"
    init_store(str(db))
    data = make_receipt_data(**_args())
    event_id = log_event("fictional-session", EventType.OBSERVATION,
                         "Fictional reservation failed", Source.SYSTEM, data=data)
    row = dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (event_id,)))
    receipt = receipt_from_event(row)
    assert receipt["event_id"] == row["event_uuid"]
    assert receipt["outcome"] == "failed"
    assert receipt["version"] == 1
    assert "summary" not in receipt and "data" not in receipt
    mirror = [json.loads(x) for x in mirror_path(db).read_text().splitlines()]
    assert receipt_from_event(mirror[0]) == receipt
    before = mirror_path(db).read_bytes()
    init_store(str(db))
    after = dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (event_id,)))
    assert receipt_from_event(after) == receipt
    assert mirror_path(db).read_bytes() == before
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"] == 1


def test_cross_module_resemblance_is_not_equivalence(tmp_path):
    db = tmp_path / "synthetic.sqlite"
    init_store(str(db))
    first = log_event("fictional-session", EventType.OBSERVATION,
                      "Fictional fixture A", Source.SYSTEM,
                      data=make_receipt_data(**_args(module="fictional.scheduler")))
    source = dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (first,)))
    relation = {"kind": "resembles", "target_event_id": source["event_uuid"],
                "evidence_refs": ["event:" + source["event_uuid"]], "uncertainty": 0.6}
    second = log_event("fictional-session", EventType.OBSERVATION,
                       "Fictional fixture B", Source.SYSTEM,
                       data=make_receipt_data(**_args(module="fictional.maintenance",
                                                     relations=[relation])))
    current = dict(get_store().fetchone("SELECT * FROM events WHERE id=?", (second,)))
    receipt = receipt_from_event(current)
    assert receipt["relations"][0]["kind"] == "resembles"
    assert receipt["relations"][0]["target_event_id"] == source["event_uuid"]
    assert receipt["event_id"] != source["event_uuid"]
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"] == 2


def test_rejects_private_fields_and_free_text():
    with pytest.raises(ValueError, match="privacy"):
        make_receipt_data(**_args(metadata={"prompt": "secret"}))
    with pytest.raises(ValueError, match="opaque"):
        make_receipt_data(**_args(evidence_refs=["/home/operator/customer.pdf"]))
    with pytest.raises(ValueError, match="neutral"):
        make_receipt_data(**_args(action="customer confidential payload"))


def test_rejects_unverified_equivalence_and_invalid_uncertainty():
    relation = {"kind": "equivalent", "target_event_id": str(uuid4()),
                "evidence_refs": [], "uncertainty": 0.0}
    with pytest.raises(ValueError, match="equivalence"):
        make_receipt_data(**_args(relations=[relation]))
    with pytest.raises(ValueError, match="uncertainty"):
        make_receipt_data(**_args(uncertainty=float("nan")))


def test_rejects_unknown_outcomes_and_unversioned_rows():
    with pytest.raises(ValueError, match="outcome"):
        make_receipt_data(**_args(outcome="it probably worked"))
    with pytest.raises(ValueError, match="no v1"):
        receipt_from_event({"data": {"legacy": True}})
