"""Verify real BEAN two-lifecycle continuity in an isolated temporary SQLite DB."""
from examples.restart_continuity import run_demo


def test_two_lifecycles_preserve_event_and_review_boundary():
    r = run_demo()
    assert r["schema"] == "bean.public.restart_proof.v1"
    assert r["provider"] == "mock_fixture_not_live_llm"
    assert r["real_sqlite_restart_test"] is True
    assert r["distinct_sessions"] is True
    assert r["boot_records_at_least"] >= 2
    assert r["persisted_event_found"] is True
    assert r["persisted_review_proposal_found"] is True
    assert r["proposal_status_after_restart"] == "pending_review"
    assert r["effectors_called"] is False
    assert r["external_requests"] is False
    assert r["database_lifetime"] == "temporary_local_only"
