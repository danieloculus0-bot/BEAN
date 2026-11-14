"""OpenNARS-inspired evidence revision tests, all records synthetic."""
import json

import pytest

from bean.cognition.evidence_revision import EvidenceReviser, SUBTYPE
from bean.memory.event_logger import (
    EventType, Source, log_event, supersede_event,
)
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.store import get_store, init_store
from bean.reasoning.context_builder import build_reasoning_context
from bean.reasoning.prompt_builder import build_ollama_prompt
from bean.runtime.inbox import InboxMessage
from bean.runtime.inbox_handlers import make_handlers
from bean.world.claim import ClaimCategory, ClaimSource, make_claim
from bean.world.model_store import ModelStore


@pytest.fixture
def core(tmp_path):
    path = tmp_path / "evidence.sqlite"
    init_store(str(path))
    bootstrap_identity()
    session = begin_session()
    ModelStore()
    yield path, session
    get_store().close()


KEY = "environment.induction.voltage"


def observe(engine, session, source, evidence, polarity):
    return engine.observe(
        session, claim_key=KEY, source_ref=source,
        evidence_ref=evidence, polarity=polarity)


def test_missing_evidence_remains_unknown(core):
    _, session = core
    e = EvidenceReviser()
    state = e.assess(KEY)
    assert state["status"] == "unknown"
    assert state["frequency"] is None
    assert state["confidence"] == 0
    assert state["expectation"] == 0.5
    assert state["claim_truth_verified"] is False


def test_two_dimensional_truth_and_opposing_evidence(core):
    _, session = core
    e = EvidenceReviser()
    observe(e, session, "probe:a", "receipt:a", "support")
    observe(e, session, "probe:b", "receipt:b", "support")
    outcome = observe(e, session, "probe:c", "receipt:c", "refute")
    assert outcome["status"] == "contested"
    assert outcome["supporting_sources"] == 2
    assert outcome["refuting_sources"] == 1
    assert outcome["frequency"] == pytest.approx(2 / 3)
    assert outcome["confidence"] == pytest.approx(3 / 4)
    assert outcome["expectation"] == pytest.approx(5 / 8)
    assert outcome["source_independence_authenticated"] is False


def test_replaying_same_receipt_never_improves_confidence(core):
    _, session = core
    e = EvidenceReviser()
    once = observe(e, session, "probe:a", "receipt:a", "support")
    for _ in range(7):
        repeat = observe(e, session, "probe:a", "receipt:a", "support")
    assert once["confidence"] == repeat["confidence"] == 0.5
    assert repeat["supporting_sources"] == 1
    assert repeat["duplicate_events_discarded"] == 7
    assert repeat["event_count"] == 8


def test_many_receipts_from_same_source_are_one_vote(core):
    _, session = core
    e = EvidenceReviser()
    for i in range(5):
        observe(e, session, "probe:one", f"receipt:{i}", "support")
    s = e.assess(KEY)
    assert s["confidence"] == 0.5
    assert s["supporting_sources"] == 1


def test_same_source_contradiction_is_not_invented_confirmation(core):
    _, session = core
    e = EvidenceReviser()
    observe(e, session, "probe:one", "receipt:one", "support")
    changed = observe(e, session, "probe:one", "receipt:two", "refute")
    assert changed["status"] == "unknown"
    assert changed["conflicted_source_refs"] == ["probe:one"]
    assert changed["confidence"] == 0
    assert changed["source_independence_authenticated"] is False


def test_shared_receipt_across_sources_is_excluded(core):
    _, session = core
    e = EvidenceReviser()
    observe(e, session, "probe:one", "receipt:shared", "support")
    changed = observe(e, session, "probe:two", "receipt:shared", "support")
    assert changed["status"] == "unknown"
    assert changed["supporting_sources"] == 0
    assert changed["conflicting_evidence_refs"] == ["receipt:shared"]


def test_superseded_event_is_excluded_from_revision(core):
    _, session = core
    e = EvidenceReviser()
    original = observe(e, session, "probe:one", "receipt:before", "support")
    corrected = observe(e, session, "probe:one", "receipt:after", "refute")
    supersede_event(original["event_id"], corrected["event_id"])
    state = e.assess(KEY)
    assert state["status"] == "one_sided_unverified"
    assert state["frequency"] == 0
    assert state["confidence"] == 0.5
    assert state["evidence_event_ids"] == [corrected["event_id"]]


def test_retains_receipts_across_restart_and_sessions(core):
    path, session = core
    e = EvidenceReviser()
    observe(e, session, "probe:one", "receipt:one", "support")
    get_store().close()
    init_store(str(path))
    next_session = begin_session()
    state = observe(EvidenceReviser(), next_session, "probe:two", "receipt:two", "refute")
    assert state["status"] == "contested"
    assert state["confidence"] == pytest.approx(2 / 3)
    assert len(state["evidence_event_ids"]) == 2


def test_incomplete_history_is_unknown_not_a_confident_partial_vote(core):
    _, session = core
    e = EvidenceReviser()
    observe(e, session, "probe:one", "receipt:one", "support")
    observe(e, session, "probe:two", "receipt:two", "refute")
    state = e.assess(KEY, max_events=1)
    assert state["status"] == "incomplete_history"
    assert state["frequency"] is None
    assert state["confidence"] is None
    assert state["history_truncated"] is True


def test_reject_invalid_polarity_and_source_without_writes(core):
    _, session = core
    e = EvidenceReviser()
    with pytest.raises(ValueError):
        observe(e, session, "probe:one", "receipt:one", "unclear")
    with pytest.raises(ValueError):
        observe(e, session, "", "receipt:one", "support")
    with pytest.raises(ValueError):
        e.assess("bad key with spaces")
    rows = get_store().fetchall(
        "SELECT * FROM events WHERE subtype=?", (SUBTYPE,))
    assert rows == []


def test_revisions_appear_in_actual_reasoning_packet_and_small_prompt(core):
    _, session = core
    ModelStore().save(make_claim(
        KEY, "Induction voltage may be 17 volts.",
        ClaimCategory.ENVIRONMENT, ClaimSource.SUPERVISOR, 0.45))
    e = EvidenceReviser()
    a = observe(e, session, "probe:one", "receipt:one", "support")
    b = observe(e, session, "probe:two", "receipt:two", "refute")
    query = log_event(session, EventType.HUMAN_INPUT,
                      "Review induction voltage", Source.HUMAN)
    packet = build_reasoning_context(session, source_event_id=query)
    revisions = packet["context"]["evidence_revisions"]
    assert len(revisions) == 1
    assert revisions[0]["status"] == "contested"
    assert revisions[0]["claim_truth_verified"] is False
    assert {a["event_id"], b["event_id"]} <= set(json.loads(
        get_store().fetchone(
            "SELECT included_event_ids_json FROM reasoning_context_packets "
            "WHERE packet_id=?", (packet["packet_id"],)
        )["included_event_ids_json"]))
    prompt = build_ollama_prompt(packet["context"])
    assert '"status":"contested"' in prompt
    assert '"source_independence_authenticated":false' in prompt


def test_runtime_inbox_records_and_assesses_actual_evidence(core):
    _, session = core
    handlers = make_handlers()
    rec = handlers["record_belief_evidence"](
        InboxMessage("record_belief_evidence", {
            "claim_key": KEY, "polarity": "support",
            "source_ref": "probe:one", "evidence_ref": "receipt:one"}),
        session)
    assert rec["success"] is True
    state = handlers["assess_belief_evidence"](
        InboxMessage("assess_belief_evidence", {"claim_key": KEY}), session)
    assert state["revision"]["supporting_sources"] == 1
    assert state["revision"]["claim_truth_verified"] is False


def test_duplicate_storm_does_not_overrule_two_opposing_sources(core):
    _, session = core
    e = EvidenceReviser()
    for _ in range(10):
        observe(e, session, "probe:one", "receipt:same", "support")
    observe(e, session, "probe:two", "receipt:two", "refute")
    result = observe(e, session, "probe:three", "receipt:three", "refute")
    assert result["frequency"] == pytest.approx(1 / 3)
    assert result["confidence"] == pytest.approx(3 / 4)
    assert result["supporting_sources"] == 1
    assert result["refuting_sources"] == 2
    # Naive un-stamped votes would incorrectly record support majority 10/12.
    assert result["duplicate_events_discarded"] == 9
