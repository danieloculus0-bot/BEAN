"""End-to-end utility smoke for actual BEAN Core components.

These are reproducible synthetic checks, never business metrics or LLM wins.
"""
from examples.capability_proof import (
    run_proof, verify_restart, verify_conflict,
    verify_guardrails, verify_missing_data,
)


def test_integrated_proof_runs_actual_core_layers_without_effects():
    report = run_proof()
    assert report["schema"] == "bean.utility.proof.v1"
    assert report["status"] == "PASS"
    assert report["checks_total"] == report["checks_passed"] == 4
    assert report["network_requests"] is False
    assert report["live_model_used"] is False
    assert report["real_erp_or_hardware_used"] is False
    assert report["business_outcome_proven"] is False
    assert all(row["status"] == "PASS" for row in report["checks"].values())


def test_restart_is_real_sqlite_but_mock_reasoning():
    result = verify_restart()
    assert result["persisted_proposal_status"] == "pending_review"
    assert result["provider"] == "mock_fixture_not_live_llm"


def test_conflict_retains_unknown_instead_of_pretending_a_vote():
    result = verify_conflict()
    assert result["verified_independent_origins"] == 0
    assert result["conclusion"] is None


def test_claim_and_action_checks_do_not_grant_permission():
    result = verify_guardrails()
    assert result["truth_verification"] == "not_performed"
    assert result["execution_permission"] == "none"


def test_missing_is_not_zero_but_evidenced_zero_is_zero():
    result = verify_missing_data()
    assert result["missing_status"] == "n/a"
    assert result["missing_value"] is None
    assert result["complete_report_status"] == "verified"
    assert result["complete_report_value"] == 0
