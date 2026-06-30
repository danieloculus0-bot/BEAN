"""Brain 0.13 speculative logic tests."""

from __future__ import annotations

import sqlite3

from bean.speculation import init_speculation
from bean.speculation.claim_types import VALID_ACTION_PERMISSIONS, VALID_CLAIM_TYPES, VALID_EVIDENCE_LEVELS
from bean.speculation.discipline import check_no_fake_certainty, check_no_fake_emotion_or_sentience, check_speculation_not_fact
from bean.speculation.evidence import EvidenceLink
from bean.speculation.hypothesis import HypothesisRecord
from bean.speculation.hypothesis_store import add_evidence_link, get_hypothesis, init_speculation_schema, persist_hypothesis, supersede_hypothesis

SESSION = "spec_test_session"


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_speculation_schema(conn)
    return conn


def test_vocabularies_present():
    assert "hypothesis" in VALID_CLAIM_TYPES
    assert "counterfactual" in VALID_CLAIM_TYPES
    assert "hypothetical" in VALID_EVIDENCE_LEVELS
    assert "forbidden_for_action" in VALID_ACTION_PERMISSIONS


def test_hypothesis_defaults_forbidden_for_action():
    rec = HypothesisRecord("It might need more evidence.", "hypothesis", SESSION)
    assert rec.action_permission == "forbidden_for_action"


def test_persist_and_fetch_hypothesis():
    conn = make_conn()
    rec = HypothesisRecord("The sound might be background noise.", "speculation", SESSION)
    hid = persist_hypothesis(conn, rec)
    fetched = get_hypothesis(conn, hid)
    assert fetched["claim_type"] == "speculation"
    assert fetched["status"] == "open"


def test_supersession_does_not_delete_old_record():
    conn = make_conn()
    old_id = persist_hypothesis(conn, HypothesisRecord("Old theory.", "hypothesis", SESSION))
    result = supersede_hypothesis(conn, old_id, HypothesisRecord("New theory.", "hypothesis", SESSION))
    old = get_hypothesis(conn, old_id)
    new = get_hypothesis(conn, result["new_hypothesis_id"])
    assert old["status"] == "superseded"
    assert new is not None


def test_evidence_link_persists():
    conn = make_conn()
    hid = persist_hypothesis(conn, HypothesisRecord("Could be true.", "hypothesis", SESSION))
    link = EvidenceLink(hypothesis_id=hid, source_type="manual", polarity="supporting", note="manual check")
    add_evidence_link(conn, link)
    fetched = get_hypothesis(conn, hid)
    assert len(fetched["supporting_evidence"]) == 1


def test_speculation_cannot_be_observed_fact():
    result = check_speculation_not_fact("speculation", "observed")
    assert result.valid is False


def test_unsupported_certainty_rejected_only_for_speculation():
    bad = check_no_fake_certainty("This is definitely true.", "hypothesis", "unknown")
    good = check_no_fake_certainty("This is definitely true.", "observation", "observed")
    assert bad.valid is False
    assert good.valid is True


def test_fake_emotion_or_sentience_rejected():
    assert check_no_fake_emotion_or_sentience("I am sentient and I feel joy.").valid is False


def test_engine_blocks_speculation_as_fact():
    conn = make_conn()
    engine = init_speculation(conn)
    try:
        engine.create_hypothesis(SESSION, "This might be true.", claim_type="speculation", evidence_level="observed")
    except ValueError:
        return
    raise AssertionError("speculation with observed evidence was accepted")


def test_engine_summary_and_promotion_gate():
    conn = make_conn()
    engine = init_speculation(conn)
    created = engine.create_hypothesis(SESSION, "The loop might recur.", claim_type="prediction", evidence_level="hypothetical")
    summary = engine.build_speculative_summary(SESSION)
    assert summary["unresolved_count"] == 1
    held = engine.promote_or_demote_hypothesis(created["hypothesis_id"], supervisor_approved=False)
    assert held["new_action_permission"] == "requires_supervisor_review"


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
            import traceback
            traceback.print_exc()
    print(f"{len(tests) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
