"""Lab 010 BEAN trust filter and care/owner-only petting tests."""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from bean.memory.store import init_store, get_store, _local
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.relationship.evidence_filter import TrustEvidenceFilter
from bean.relationship.care import CareMemory, LOVE_PRINCIPLES
from bean.relationship.trust_model import TrustModel
from bean.relationship.interaction_tracker import _is_pretend_request


@pytest.fixture
def env(tmp_path):
    if getattr(_local, "conn", None):
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "lab010.sqlite"))
    bootstrap_identity()
    return begin_session()


def add(filter_, id, subject="human_1", domain="corrections", origin="source_1",
        outcome="success", verified=True, t=None):
    return filter_.record(
        evidence_id=id, subject_id=subject, domain=domain, origin_id=origin,
        outcome=outcome, verified=verified,
        verifier_ref=("checked:" + id) if verified else None,
        observed_at=t or datetime(2026, 10, 10, 12, tzinfo=timezone.utc))


def test_default_is_not_earned_trust(env):
    result = TrustEvidenceFilter().evaluate(
        "human_1", "corrections", as_of="2026-10-10T13:00:00+00:00")
    assert result["estimate"] == 0.5
    assert result["verdict"] == "insufficient_evidence"


def test_synthetic_verified_outcomes_and_independent_origins(env):
    f = TrustEvidenceFilter()
    for i in range(12):
        add(f, f"valid-{i}", origin=f"origin_{i}")
    r = f.evaluate("human_1", "corrections", as_of="2026-10-10T13:00:00Z")
    assert r["estimate"] > 0.85
    assert r["independent_origins"] == 12
    assert r["verdict"] == "supported"


def test_unverified_and_correlated_repeats_cannot_boost_reliability(env):
    f = TrustEvidenceFilter()
    for i in range(50):
        add(f, f"unverified-{i}", origin=f"unsafe_{i}", verified=False)
        add(f, f"echo-{i}", origin="shared_syndicate")
    r = f.evaluate("human_1", "corrections", as_of="2026-10-10T13:00:00Z")
    assert r["independent_origins"] == 1
    assert r["verdict"] == "insufficient_evidence"
    assert len(r["excluded_unverified"]) == 50


def test_domain_isolation_and_contradictions(env):
    f = TrustEvidenceFilter()
    t = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    add(f, "first", origin="origin_a", t=t)
    add(f, "newer", origin="origin_a", outcome="failure", t=t + timedelta(minutes=1))
    add(f, "other", domain="electronics", origin="origin_b")
    r = f.evaluate("human_1", "corrections", as_of=t + timedelta(hours=1))
    older = f.evaluate("human_1", "corrections", as_of=t + timedelta(seconds=30))
    assert len(r["receipts"]) == 1 and r["receipts"][0]["outcome"] == "failure"
    assert older["receipts"][0]["outcome"] == "success"
    assert f.evaluate("human_1", "electronics", as_of=t + timedelta(hours=1))["estimate"] > 0.5


def test_decay_is_as_of_not_retroactive(env):
    f = TrustEvidenceFilter()
    t = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    add(f, "old", t=t)
    then = f.evaluate("human_1", "corrections", as_of=t + timedelta(seconds=1))
    now = f.evaluate("human_1", "corrections", as_of=t + timedelta(days=360))
    assert then["estimate"] > now["estimate"] > 0.5
    assert now["verdict"] == "insufficient_evidence"


def test_immutable_id_and_source_ref(env):
    f = TrustEvidenceFilter()
    add(f, "same")
    assert add(f, "same") is False
    with pytest.raises(ValueError, match="immutable"):
        add(f, "same", outcome="failure")
    with pytest.raises(ValueError, match="verifier reference"):
        f.record(evidence_id="bad", subject_id="a", domain="b",
                 origin_id="c", outcome="success", verified=True)


def test_real_bean_epistemic_filter(env):
    f = TrustEvidenceFilter()
    for i in range(8):
        add(f, f"src_{i}", origin=f"independent_{i}")
    result = TrustModel().assess_domain(
        "human_1", "corrections", as_of="2026-10-10T13:00:00+00:00")
    assert result["bean_audit"]["verdict"] == "approved"
    assert get_store().fetchone(
        "SELECT COUNT(*) AS n FROM epistemic_audits WHERE candidate_key='trust.reliability.corrections'")["n"] == 1


def test_questions_roleplay_affection_do_not_penalize_legacy_trust(env):
    assert not _is_pretend_request({
        "summary": "Can you feel love, or pretend to care?",
        "data": {"from": "primary_developer", "command": "ask"}
    })
    assert _is_pretend_request({"data": {"command": "pretend"}})
    t = TrustModel()
    assert t.apply_evidence("primary_developer", "asked_to_pretend",
                            "A consensual puppy game")["new_score"] == 0.5
    assert t.apply_evidence("primary_developer", "unsupported_claim_request",
                            "Unverified classifier")["new_score"] == 0.5


def test_owner_only_petting_does_not_depend_on_trust(env):
    c = CareMemory()
    concept = c.understand_love()
    assert "patient teaching" in concept["principle"]
    assert concept["experience_claim"] == "not_established"
    assert c.pet(authenticated_principal=None)["accepted"] is False
    assert c.pet(authenticated_principal="friend")["accepted"] is False
    # High reliability is not proof of permission.
    TrustModel().apply_evidence("friend", "confirmed_test_result", "Verified test")
    assert c.pet(authenticated_principal="friend")["accepted"] is False
    assert c.pet(authenticated_principal="primary_developer", note="gentle puppy pet")["accepted"] is True
    assert len(c.pet_history()) == 1
    assert c.pet_history()[0]["actor_id"] == "primary_developer"


def test_love_principles_are_present_in_reconstructed_context(env):
    from bean.reasoning.context_builder import build_reasoning_context
    packet = build_reasoning_context(env)
    care = packet["context"]["care_and_love"]
    assert care["petting_permission"] == "owner_only"
    assert "sustained care" in care["love_definition"]
    assert packet["context"]["identity_rules"]["affection_is_not_trust_or_access"]
    CareMemory().pet(authenticated_principal="primary_developer")
    packet2 = build_reasoning_context(env)
    assert len(packet2["context"]["care_and_love"]["recent_verified_pet_events"]) == 1


def test_recorded_petting_does_not_inflate_trust(env):
    c = CareMemory()
    before = TrustModel().run_review("primary_developer")["new_score"]
    for i in range(10):
        assert c.pet(authenticated_principal="primary_developer", note=f"pet {i}")["accepted"]
    after = TrustModel().run_review("primary_developer")["new_score"]
    assert before == after == 0.5


def test_important_reasoning_note_survives_reconstructed_context(env):
    from bean.reasoning.context_builder import build_reasoning_context
    first = build_reasoning_context(env)["context"]
    second = build_reasoning_context(env)["context"]
    for context in (first, second):
        assert context["identity_rules"]["revise_interpretations_on_new_context"]
        notes = context["important_reasoning_notes"]
        assert len(notes) >= 1
        note = next(n for n in notes if n["id"] == "BEAN_REASONING_001")
        assert note["priority"] == "important"
        assert "reconsider the explanation" in note["principle"]
        assert any("observations" in step and "interpretations" in step for step in note["procedure"])
        assert any("coherent objective" in step for step in note["procedure"])
        assert any("insufficient_evidence" in step for step in note["procedure"])
    assert first["important_reasoning_notes"] == second["important_reasoning_notes"]
