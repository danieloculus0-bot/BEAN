"""Cross-domain evidence ranking and Core integration regression tests."""
from datetime import datetime, timezone, timedelta
import sqlite3
import pytest

from bean.evaluation.evidence_rank import Evidence, EvidenceRankLedger
from bean.integration.reasoning_layer import BeanReasoningLayer
from bean.integration.evidence_bridge import EvidenceBridge, SourceClaim

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def source(name, domain="manufacturing", topic="quality", value="pass", *,
           origin=None, verified=True, outcome="unmeasured", days=0):
    return Evidence(
        evidence_id=name, domain=domain, topic=topic, value=value,
        origin=origin or name, source_ref=f"source:{name}",
        verified=verified,
        verification_ref=f"verification:{name}" if verified else None,
        observed_at=(NOW - timedelta(days=days)).isoformat(),
        outcome=outcome,
        outcome_ref=f"independent-test:{name}" if outcome != "unmeasured" else None,
    )


def ledger():
    return EvidenceRankLedger(sqlite3.connect(":memory:"))


def test_scored_before_hashing_with_idempotent_chain():
    l = ledger()
    first = l.observe(source("qa_1"), as_of=NOW)
    assert first["intake_score"] == 40 and len(first["hash"]) == 64
    second = l.observe(source("qa_2"), as_of=NOW)
    assert second["intake_score"] == 54
    assert l.verify_chain()
    assert not l.observe(source("qa_1"), as_of=NOW)["new"]
    assert l.rank("manufacturing", "quality", as_of=NOW)[0]["status"] == "attested"


def test_duplicate_origin_cannot_inflate_independent_evidence():
    l = ledger()
    l.observe(source("copy_1", origin="same_publisher"), as_of=NOW)
    l.observe(source("copy_2", origin="same_publisher"), as_of=NOW)
    x = l.rank("manufacturing", "quality", as_of=NOW)[0]
    assert x["distinct_verified_origins"] == 1
    assert x["status"] == "insufficient" and x["score"] == 40


def test_contradictions_stay_visible_without_forced_consensus():
    l = ledger()
    l.observe(source("a", value="works"), as_of=NOW)
    l.observe(source("b", value="fails"), as_of=NOW)
    rows = l.rank("manufacturing", "quality", as_of=NOW)
    assert {x["status"] for x in rows} == {"contested"}
    assert all(x["opposing_verified_origins"] == 1 for x in rows)


def test_empirically_attested_outcomes_revise_quality_not_truth():
    l = ledger()
    l.observe(source("c1", outcome="pass"), as_of=NOW)
    l.observe(source("c2", outcome="pass"), as_of=NOW)
    x = l.rank("manufacturing", "quality", as_of=NOW)[0]
    assert x["score"] == 70
    assert x["score_is_truth_probability"] is False
    l.observe(source("c3", outcome="fail"), as_of=NOW)
    assert l.rank("manufacturing", "quality", as_of=NOW)[0]["score"] < 84


def test_unverified_volume_does_not_invent_attestation():
    l = ledger()
    for i in range(12):
        l.observe(source(f"copy{i}", verified=False), as_of=NOW)
    x = l.rank("manufacturing", "quality", as_of=NOW)[0]
    assert x["status"] == "insufficient" and x["score"] == 12


def test_age_penalty_and_new_attestation_revise_strength():
    l = ledger()
    l.observe(source("old", days=130), as_of=NOW)
    score = l.rank("manufacturing", "quality", as_of=NOW)[0]["score"]
    l.observe(source("new"), as_of=NOW)
    assert l.rank("manufacturing", "quality", as_of=NOW)[0]["score"] > score


def test_one_ranker_handles_three_different_subject_domains():
    l = ledger()
    for domain, topic, value in [
        ("trading", "candidate_alpha", "beats_cash"),
        ("weather", "tomorrow_high", "62F"),
        ("manufacturing", "inspection_10", "pass"),
    ]:
        l.observe(source(domain+"1", domain, topic, value), as_of=NOW)
        l.observe(source(domain+"2", domain, topic, value), as_of=NOW)
        assert l.rank(domain, topic, as_of=NOW)[0]["status"] == "attested"
    assert l.rank("unknown", "missing", as_of=NOW) == []


def test_refuses_invented_outcome_futures_and_evidence_id_collision():
    l = ledger()
    with pytest.raises(ValueError, match="measured outcomes"):
        source("bad", verified=False, outcome="pass")
    with pytest.raises(ValueError, match="future"):
        l.observe(Evidence("future", "weather", "temp", "32", "station", "ref",
                           (NOW + timedelta(days=1)).isoformat()), as_of=NOW)
    l.observe(source("known"), as_of=NOW)
    with pytest.raises(ValueError, match="collision"):
        l.observe(source("known", value="other"), as_of=NOW)


def test_historical_ranking_does_not_use_later_incoming_records():
    l = ledger()
    l.observe(source("first"), as_of=NOW)
    l.observe(source("second"), as_of=NOW + timedelta(days=30))
    old = l.rank("manufacturing", "quality", as_of=NOW)[0]
    new = l.rank("manufacturing", "quality", as_of=NOW + timedelta(days=30))[0]
    assert old["distinct_verified_origins"] == 1
    assert new["distinct_verified_origins"] == 2


def test_hash_tampering_fails_on_restart(tmp_path):
    db = tmp_path / "rank.sqlite"
    conn = sqlite3.connect(db)
    l = EvidenceRankLedger(conn)
    l.observe(source("original"), as_of=NOW)
    conn.close()
    conn = sqlite3.connect(db)
    assert EvidenceRankLedger(conn).rank("manufacturing", "quality", as_of=NOW)
    conn.execute("UPDATE bean_ranked_evidence SET intake_score=99")
    conn.commit()
    with pytest.raises(ValueError, match="chain"):
        EvidenceRankLedger(conn)
    conn.close()


def test_bridge_scores_before_filing_and_survives_core_restart(tmp_path):
    path = str(tmp_path / "bean.db")
    with BeanReasoningLayer(path) as core:
        bridge = EvidenceBridge(core)
        bridge.start("first_round", "first_article", "Did the inspection pass?")
        first = SourceClaim("a", "first_round", "inspector_a", "report:a",
                            "pass", True, "verification:a", "2026-10-10T12:00:00Z")
        second = SourceClaim("b", "first_round", "inspector_b", "report:b",
                             "pass", True, "verification:b", "2026-10-10T12:00:00Z")
        bridge.observe(first)
        rows = core.store.fetchall("SELECT intake_score,entry_hash FROM bean_ranked_evidence")
        assert len(rows) == 1 and rows[0]["intake_score"] >= 0 and rows[0]["entry_hash"]
        bridge.observe(second)
        assert bridge.finalize("first_round")["status"] == "confirmed"
        ranked = core.evidence_ranker().rank("external", "first_article")
        assert ranked[0]["status"] == "attested"
        assert ranked[0]["distinct_verified_origins"] == 2

    with BeanReasoningLayer(path) as core:
        ranked = core.evidence_ranker().rank("external", "first_article")
        assert ranked[0]["status"] == "attested"
        assert core.evidence_ranker().verify_chain()


def test_failed_bridge_insert_rolls_back_scored_receipt(tmp_path):
    with BeanReasoningLayer(str(tmp_path / "bean.sqlite")) as core:
        bridge = EvidenceBridge(core)
        bridge.start("same_round", "check", "Check source duplication?")
        bridge.observe(SourceClaim(
            "id_a", "same_round", "inspector_a", "same:source",
            "pass", True, "verified:a", "2026-10-10T12:00:00Z",
        ))
        with pytest.raises(ValueError, match="duplicate"):
            bridge.observe(SourceClaim(
                "id_b", "same_round", "inspector_b", "same:source",
                "pass", True, "verified:b", "2026-10-10T12:00:00Z",
            ))
        rows = core.store.fetchall("SELECT evidence_id FROM bean_ranked_evidence")
        assert len(rows) == 1 and rows[0]["evidence_id"].endswith("id_a")
