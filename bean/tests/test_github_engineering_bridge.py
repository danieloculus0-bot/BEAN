"""Offline evidence, continuity and adverse-input tests for GitHub Engineering Bridge."""
import json
import sqlite3

import pytest

from bean.integration.github_engineering import (
    EngineeringJournal, GitHubReadClient, run_bridge,
)


def remote_fixture(*, failed=True):
    return {
        "/branches?per_page=100": [
            {"name": "main", "commit": {"sha": "a" * 40}, "protected": True},
            {"name": "experiment/peer-lab", "commit": {"sha": "b" * 40}, "protected": False},
        ],
        "/pulls?state=open&per_page=100": [{
            "number": 74, "title": "BEAN neural repair experiment",
            "html_url": "https://github.com/danieloculus0-bot/BEAN/pull/74",
            "head": {"ref": "experiment/peer-lab", "sha": "b" * 40},
            "base": {"ref": "main"}, "state": "open", "draft": True,
            "updated_at": "2026-10-11T07:00:00Z",
        }],
        "/actions/runs?per_page=50": {
            "workflow_runs": [
                {"id": 12345, "name": "BEAN CI peer test",
                 "head_branch": "experiment/peer-lab", "head_sha": "b" * 40,
                 "status": "completed",
                 "conclusion": "failure" if failed else "success",
                 "html_url": "https://github.com/danieloculus0-bot/BEAN/actions/runs/12345",
                 "pull_requests": [{"number": 74}],
                 "updated_at": "2026-10-11T07:04:00Z"},
            ]
        },
    }


def test_bridge_discovers_repos_prs_and_ci_and_builds_evidence_queue(tmp_path):
    db = tmp_path / "bean.db"
    payload = remote_fixture()
    result = run_bridge(
        "danieloculus0-bot/BEAN", db,
        fetch_json=lambda endpoint: payload[endpoint],
    )
    assert result["mode"] == "read_only"
    assert result["new_events"] == 4
    assert result["counts"] == {"branches": 2, "pull_requests": 1, "workflow_runs": 1}
    assert result["work_queue"][0]["priority"] == "investigate"
    assert result["work_queue"][0]["related_pull_requests"] == [74]
    assert result["work_queue"][0]["next_role"] == "reviewer"
    assert result["work_queue"][0]["conclusion"] == "failure"
    assert "/actions/runs/12345" in result["work_queue"][0]["url"]
    assert result["work_queue"][1]["next_role"] == "tester"

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM github_engineering_events").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM github_engineering_syncs").fetchone()[0] == 1


def test_restart_retains_history_without_rewriting_same_receipts(tmp_path):
    db = tmp_path / "bean.db"
    remote = remote_fixture()
    first = run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    second = run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    assert first["new_events"] == 4
    assert second["new_events"] == 0
    remote = remote_fixture(failed=False)
    third = run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    assert third["new_events"] == 1
    assert third["work_queue"][0]["subject"] == "pull_request"
    journal = EngineeringJournal(db)
    try:
        journal.verify()
    finally:
        journal.close()


def test_changed_ci_outcome_records_a_new_receipt_after_reversion(tmp_path):
    db = tmp_path / "bean.db"
    for failed in [True, False, True]:
        remote = remote_fixture(failed=failed)
        run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM github_engineering_events WHERE kind='workflow_run'"
        ).fetchone()[0] == 3


def test_tampering_is_detected_on_next_sync(tmp_path):
    db = tmp_path / "bean.db"
    remote = remote_fixture()
    run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE github_engineering_events SET payload_json=? WHERE id=1",
                     ('{"name":"rewritten"}',))
    with pytest.raises(ValueError, match="modified"):
        run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)


def test_remote_failure_does_not_create_unverified_receipts(tmp_path):
    db = tmp_path / "bean.db"

    def broken(endpoint):
        if endpoint.startswith("/pulls"):
            raise RuntimeError("GitHub rate limited")
        return remote_fixture()[endpoint]

    with pytest.raises(RuntimeError, match="rate limited"):
        run_bridge("danieloculus0-bot/BEAN", db, fetch_json=broken)
    assert not db.exists()


def test_bad_repository_and_unapproved_api_paths_are_rejected():
    for repo in ("https://example.com/BEAN", "../BEAN", "danieloculus0-bot/../BEAN",
                 "danieloculus0-bot/BEAN/other", "danieloculus0-bot"):
        with pytest.raises(ValueError):
            GitHubReadClient(repo)
    with pytest.raises(ValueError, match="unsupported"):
        GitHubReadClient("danieloculus0-bot/BEAN").get("/actions/runs/12345/dispatches")


def test_tokens_are_not_persisted_or_printed(tmp_path, monkeypatch):
    secret = "sensitive-GitHub-token-do-not-save"
    monkeypatch.setenv("GH_TOKEN", secret)
    remote = remote_fixture()
    db = tmp_path / "bean.db"
    run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT payload_json FROM github_engineering_events").fetchall()
    assert secret not in json.dumps([tuple(row) for row in rows])
    assert secret not in db.read_bytes().decode("utf-8", errors="ignore")


def test_bounded_pagination_is_flagged_not_claimed_complete():
    remote = remote_fixture()
    remote["/branches?per_page=100"] = [
        {"name": "lab-" + str(i), "commit": {"sha": str(i)}} for i in range(100)
    ]
    result = GitHubReadClient(
        "danieloculus0-bot/BEAN", fetch_json=remote.__getitem__,
    ).snapshot()
    assert result["may_be_paginated"]["branches"] is True
    assert result["counts"]["branches"] == 100


def test_rejects_broken_remote_shapes():
    remote = remote_fixture()
    remote["/actions/runs?per_page=50"] = {"workflow_runs": "not a list"}
    with pytest.raises(ValueError, match="runs shape"):
        GitHubReadClient("danieloculus0-bot/BEAN", fetch_json=remote.__getitem__).snapshot()


def test_newer_success_supersedes_old_failed_ci_in_priority_queue(tmp_path):
    db = tmp_path / "bean.db"
    remote = remote_fixture(failed=True)
    remote["/actions/runs?per_page=50"]["workflow_runs"].insert(0, {
        "id": 12346, "name": "BEAN CI peer test",
        "head_branch": "experiment/peer-lab", "head_sha": "b" * 40,
        "status": "completed", "conclusion": "success",
        "html_url": "https://github.com/danieloculus0-bot/BEAN/actions/runs/12346",
        "pull_requests": [{"number": 74}],
        "updated_at": "2026-10-11T07:06:00Z",
    })
    result = run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    assert not any(item["subject"] == "workflow_run" for item in result["work_queue"])
    # A historical failed receipt is still available in BEAN's SQLite history.
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM github_engineering_events WHERE kind='workflow_run'"
        ).fetchone()[0] == 2


def test_newer_running_ci_also_supersedes_prior_failure(tmp_path):
    db = tmp_path / "bean.db"
    remote = remote_fixture(failed=True)
    remote["/actions/runs?per_page=50"]["workflow_runs"].insert(0, {
        "id": 12346, "name": "BEAN CI peer test",
        "head_branch": "experiment/peer-lab", "head_sha": "b" * 40,
        "status": "in_progress", "conclusion": None,
        "html_url": "https://github.com/danieloculus0-bot/BEAN/actions/runs/12346",
        "pull_requests": [{"number": 74}],
        "updated_at": "2026-10-11T07:06:00Z",
    })
    result = run_bridge("danieloculus0-bot/BEAN", db, fetch_json=remote.__getitem__)
    assert not any(item["subject"] == "workflow_run" for item in result["work_queue"])
