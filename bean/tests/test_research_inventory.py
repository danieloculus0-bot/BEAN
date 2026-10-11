"""Offline contract tests for the read-only cross-repository audit inventory."""
from __future__ import annotations

import pytest

from scripts.audit_research_inventory import (
    REPOSITORIES, GitHubReader, audit_repository, category,
    render_markdown, summarize_compare, summarize_tree,
)


def test_tree_inventory_rejects_incomplete_github_tree():
    tree = {"truncated": False, "tree": [
        {"type": "blob", "path": "bean/tests/test_memory_core.py"},
        {"type": "blob", "path": ".github/workflows/brain-smoke.yml"},
        {"type": "blob", "path": "experiments/cases.json"},
        {"type": "tree", "path": "bean"},
    ]}
    result = summarize_tree(tree)
    assert result["file_count"] == 3
    assert result["test_files"] == ["bean/tests/test_memory_core.py"]
    assert len(result["workflow_files"]) == 1
    assert result["experiment_files"] == ["experiments/cases.json"]
    with pytest.raises(ValueError, match="truncated"):
        summarize_tree({"truncated": True, "tree": []})


def test_comparison_is_explicitly_not_a_feature_merge_or_test_verdict():
    result = summarize_compare("experiment/example", {
        "status": "diverged", "ahead_by": 3, "behind_by": 8,
        "files": [{"filename": "bean/tests/test_demo.py"},
                  {"filename": ".github/workflows/example.yml"}],
    })
    assert result["classification"] == "review diff: unique ancestry commits"
    assert result["touches_tests"] is True
    assert result["touches_workflows"] is True
    assert "squash" in result["caution"].lower()
    empty = summarize_compare("fix/old", {
        "status": "behind", "ahead_by": 0, "behind_by": 5, "files": [],
    })
    assert empty["classification"] == "no unique ancestry commits"
    assert category("experiment/test") == "experiment"


def test_review_inventory_produces_evidence_for_both_repos_without_mutation():
    class Stub:
        def __init__(self):
            self.calls = []

        def get(self, repo, path):
            self.calls.append((repo, path))
            if path == "/branches/main":
                return {"commit": {"sha": "a" * 40}}
            if path == "/git/trees/main?recursive=1":
                return {"truncated": False, "tree": [
                    {"type": "blob", "path": "tests/test_bridge.py"},
                ]}
            if path == "/compare/" + "a" * 40 + "..." + "b" * 40:
                return {"status": "ahead", "ahead_by": 1,
                        "behind_by": 0, "files": [{"filename": "tests/test_bridge.py"}]}
            raise AssertionError("Unexpected read: " + path)

        def pages(self, repo, path):
            self.calls.append((repo, path))
            if path == "/branches":
                return [{"name": "main", "commit": {"sha": "a" * 40}},
                        {"name": "experiment/test", "commit": {"sha": "b" * 40}}]
            if path == "/pulls?state=open":
                return [{"number": 7, "title": "Independent test", "draft": True,
                         "head": {"ref": "experiment/test"}, "base": {"ref": "main"},
                         "html_url": "https://github.com/example/repo/pull/7"}]
            raise AssertionError("Unexpected listing")

    reader = Stub()
    reports = [audit_repository(reader, repo) for repo in REPOSITORIES]
    assert len(reports) == 2
    assert all(r["branch_count"] == 2 for r in reports)
    assert all(r["branches"][0]["ahead_by"] == 1 for r in reports)
    assert all(not r["comparison_errors"] for r in reports)
    report = render_markdown(reports)
    assert "BEAN-AI-Bridge-" in report and "Independent test" in report
    assert all(path.startswith("/") for _, path in reader.calls)
    assert len(reader.calls) == 10


def test_reader_refuses_arbitrary_repository_or_host():
    reader = GitHubReader()
    with pytest.raises(ValueError, match="unapproved"):
        reader.get("attacker/private-repo", "/branches/main")
    with pytest.raises(ValueError, match="unapproved"):
        reader.get(REPOSITORIES[0], "https://attacker.example/steal")
