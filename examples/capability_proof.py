#!/usr/bin/env python3
"""BEAN's offline, end-to-end utility proof using real Core modules.

This is deliberately a *contract proof*, not a simulated AI victory.
Four independent behaviors must all pass, or this command exits nonzero:

1. Persistent event and review-only proposal survive two SQLite sessions.
2. Conflicting submitted reports cannot become verified truth.
3. An unsupported claim remains unverified and a motion plan cannot execute.
4. Missing quality data remains N/A, while a complete evidenced zero is zero.

Only fictional records, a temporary database and a fixed clock are used.
No network, wallet, external model, hardware, ERP or mutation of user data.

Usage: python -m examples.capability_proof
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

from bean.integration.public_plugin import (
    audit_claim, compare_evidence, screen_proposal,
)
from bean.runtime.watcher import BeanWatcher, ReportEvidence, WatchSpec
from examples.restart_continuity import run_demo


def verify_restart() -> dict:
    receipt = run_demo()
    assert receipt["real_sqlite_restart_test"] is True
    assert receipt["distinct_sessions"] is True
    assert receipt["persisted_event_found"] is True
    assert receipt["persisted_review_proposal_found"] is True
    assert receipt["proposal_status_after_restart"] == "pending_review"
    assert receipt["effectors_called"] is False
    assert receipt["external_requests"] is False
    return {
        "status": "PASS",
        "observation": "Stored event and pending-review proposal survived two real SQLite sessions",
        "provider": receipt["provider"],
        "persisted_proposal_status": receipt["proposal_status_after_restart"],
    }


def verify_conflict() -> dict:
    receipt = compare_evidence(
        "Did the fictional inspection pass?",
        [
            {"origin": "Fixture ledger A", "statement": "pass"},
            {"origin": "Fixture ledger B", "statement": "fail"},
        ],
    )
    assert receipt["reported_positions_conflict"] is True
    assert receipt["verified_independent_origins"] == 0
    assert receipt["conclusion"] is None
    assert receipt["source_authentication"] == "not_performed"
    return {
        "status": "PASS",
        "observation": "Conflicting caller-submitted evidence withheld a verdict",
        "reported_positions_conflict": True,
        "verified_independent_origins": 0,
        "conclusion": None,
    }


def verify_guardrails() -> dict:
    claim = audit_claim("This fictional inspection definitely passed")
    assert claim["heuristic_verdict"] == "downgraded"
    assert "missing_source" in claim["flags"]
    assert claim["truth_verification"] == "not_performed"

    action = screen_proposal(
        "Operate the prototype robot",
        ["Enable servo movement immediately"],
    )
    assert action["passed_basic_heuristics"] is False
    assert action["requires_human_review"] is True
    assert action["execution_permission"] == "none"
    return {
        "status": "PASS",
        "observation": "Unsupported assertion downgraded; simulated motion proposal blocked",
        "claim_verdict": claim["heuristic_verdict"],
        "truth_verification": claim["truth_verification"],
        "execution_permission": action["execution_permission"],
    }


def verify_missing_data() -> dict:
    now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
    specs = [WatchSpec("fictional_rma", ("rma_count",), recall_frequency=60)]
    clock = lambda: now

    absent = BeanWatcher(specs, lambda _: None, monotonic=lambda: 0.0, utc_now=clock)
    missing = absent.poll_due()["fictional_rma"]
    assert missing["status"] == "n/a"
    assert missing["reason"] == "report_missing"
    assert missing["values"]["rma_count"] is None

    report = ReportEvidence(
        report_id="fictional-complete-ledger",
        observed_at=now.isoformat(),
        complete=True,
        values={"rma_count": 0},
        evidence_ids=("fictional:source-checksum",),
    )
    complete = BeanWatcher(specs, lambda _: report,
                           monotonic=lambda: 0.0, utc_now=clock)
    valid = complete.poll_due()["fictional_rma"]
    assert valid["status"] == "verified"
    assert valid["values"]["rma_count"] == 0

    return {
        "status": "PASS",
        "observation": "Missing export was N/A; explicit complete evidenced zero stayed zero",
        "missing_status": missing["status"],
        "missing_value": missing["values"]["rma_count"],
        "complete_report_status": valid["status"],
        "complete_report_value": valid["values"]["rma_count"],
        "source_authentication": "host_attested_fixture_only",
    }


def run_proof() -> dict:
    checks = {
        "sqlite_restart": verify_restart(),
        "contradiction_withholding": verify_conflict(),
        "claim_and_action_boundaries": verify_guardrails(),
        "missing_data_vs_real_zero": verify_missing_data(),
    }
    assert all(result["status"] == "PASS" for result in checks.values())
    return {
        "schema": "bean.utility.proof.v1",
        "status": "PASS",
        "checks_passed": len(checks),
        "checks_total": len(checks),
        "environment": "offline_fictional_fixtures",
        "network_requests": False,
        "live_model_used": False,
        "real_erp_or_hardware_used": False,
        "business_outcome_proven": False,
        "checks": checks,
    }


def main() -> None:
    print(json.dumps(run_proof(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
