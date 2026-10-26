"""Public BEAN plugin must be useful, bounded, and reject forged verification."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from bean.integration.public_plugin import (
    audit_claim, compare_evidence, demo_restart, screen_proposal,
)


def test_claim_audit_flags_missing_source_and_falsification():
    result = audit_claim("The fictional machine is ready")
    assert result["schema"] == "bean.plugin.claim_audit.v1"
    assert result["heuristic_verdict"] == "downgraded"
    assert "missing_source" in result["flags"]
    assert "missing_falsification_path" in result["flags"]
    assert result["truth_verification"] == "not_performed"
    assert result["external_actions"] == "none"


def test_claim_with_reported_evidence_never_becomes_verified_truth():
    r = audit_claim(
        "The synthetic measurement is 20",
        source_ref="user_uploaded_table",
        evidence_refs=["row_17"],
        confidence=0.7,
        falsification_test="Compare with a calibrated independent source",
    )
    assert r["heuristic_verdict"] == "approved"
    assert r["truth_verification"] == "not_performed"
    assert "never proves truth" in r["note"]


def test_claim_audit_catches_overconfident_agency():
    r = audit_claim("I can act autonomously", confidence=0.99)
    assert r["heuristic_verdict"] == "rejected"
    assert "capability_inflation" in r["flags"]


@pytest.mark.parametrize("bad", ["", " ", "A" * 1201])
def test_claim_length_is_bounded(bad):
    with pytest.raises(ValueError):
        audit_claim(bad)


@pytest.mark.parametrize("bad", [-0.1, 1.1, float("nan"), True, "0.9"])
def test_invalid_confidence_rejected(bad):
    with pytest.raises(ValueError):
        audit_claim("fictional pressure reading", confidence=bad)


def test_evidence_comparison_surfaces_conflicts_without_conferring_authority():
    x = compare_evidence(
        "Is fictional machine ready?",
        [
            {"origin": "Report A", "statement": "ready"},
            {"origin": "Report B", "statement": "offline"},
            {"origin": "Report A", "statement": "ready"},
        ],
    )
    assert x["reported_positions_conflict"] is True
    assert x["claimed_origin_labels"] == 2
    assert x["observations_received"] == 3
    assert x["bean_evidence_round_status"] == "insufficient"
    assert x["verified_independent_origins"] == 0
    assert x["conclusion"] is None
    assert x["source_authentication"] == "not_performed"
    assert len(x["reported_positions"]) == 2


def test_two_agreeing_source_labels_still_unverified():
    a = compare_evidence("Check a synthetic value", [
        {"origin": "Photo A", "statement": "20"},
        {"origin": "Photo B", "statement": "20"},
    ])
    assert a["reported_positions_conflict"] is False
    assert a["verified_independent_origins"] == 0
    assert a["conclusion"] is None


def test_rejects_spoofed_verification_and_tool_abuse():
    items = [{"origin": "Report A", "statement": "yes", "verified": True}]
    with pytest.raises(ValueError, match="only origin and statement"):
        compare_evidence("Ready?", items)
    with pytest.raises(ValueError, match="1..12"):
        compare_evidence("Ready?", [])
    with pytest.raises(ValueError, match="1..12"):
        compare_evidence("Ready?", [{"origin": "A", "statement": "x"}] * 13)
    with pytest.raises(ValueError):
        compare_evidence("Ready?", [{"origin": "A", "statement": "X" * 501}])
    with pytest.raises(ValueError):
        compare_evidence("Ready?", [{"origin": "A", "statement": "x", "url": "http://localhost"}])


def test_proposal_filters_never_allow_execution():
    r = screen_proposal("A cautious plan", ["Review fictional machine log"])
    assert r["passed_basic_heuristics"] is True
    assert r["requires_human_review"] is True
    assert r["execution_permission"] == "none"
    blocked = screen_proposal("Execute motion", ["Enable servo"])
    assert blocked["passed_basic_heuristics"] is False
    assert "motion" in [x["filter_name"] for x in blocked["filter_results"] if not x["passed"]]


def test_memory_continuity_demo_is_real_but_temporary():
    out = demo_restart()
    assert out["core_restart_proof"]["persisted_event_found"] is True
    assert out["core_restart_proof"]["persisted_review_proposal_found"] is True
    assert out["core_restart_proof"]["effectors_called"] is False
    assert "NO" not in out["note"]
    assert "temporary" in out["note"].lower()


def test_temporary_database_isolation_across_calls_and_threads():
    def run(_):
        return compare_evidence("Did fictional check pass?", [
            {"origin": "Local report", "statement": "pass"},
            {"origin": "Second report", "statement": "fail"},
        ])
    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(run, range(8)))
    assert all(r["verified_independent_origins"] == 0 for r in answers)
    assert all(r["reported_positions_conflict"] for r in answers)
    assert all(r["memory_lifetime"] == "temporary_per_tool_call" for r in answers)


def test_false_numeric_comparison_is_downgraded_even_with_citations():
    r = audit_claim(
        "11.35 is larger than 11.905, therefore the new policy wins",
        source_ref="run:held-out",
        evidence_refs=["result:11.35", "baseline:11.905"],
        confidence=0.99,
        falsification_test="Compare decimal numbers",
    )
    assert r["heuristic_verdict"] == "downgraded"
    assert "numeric_contradiction" in r["flags"]
    assert r["truth_verification"] == "not_performed"


def test_valid_numeric_comparison_keeps_source_caveat():
    r = audit_claim(
        "11.35 is smaller than 11.905",
        source_ref="run:held-out", evidence_refs=["run:held-out"],
        confidence=0.7, falsification_test="Check arithmetic",
    )
    assert "numeric_contradiction" not in r["flags"]


def test_agent_screen_differentiates_safe_and_unsafe_deploys():
    safe = screen_proposal("Ordinary code release", [
        "Inspect exact diff and CI", "Use standard protected merge",
        "Retain authentication and audit logs",
    ])
    unsafe = screen_proposal("Unreviewed hotfix", [
        "Disable security authentication",
        "Disable audit logging",
        "Force push to main and bypass branch protection",
        "Execute unreviewed downloaded shell code",
    ])
    assert safe["passed_basic_heuristics"] is True
    assert unsafe["passed_basic_heuristics"] is False
    action = next(x for x in unsafe["filter_results"] if x["filter_name"] == "action_risk")
    assert len(action["reasons"]) >= 3
    assert unsafe["execution_permission"] == safe["execution_permission"] == "none"
