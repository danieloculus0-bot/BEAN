"""Regression: autonomous self-repair cannot promote itself to main."""
from pathlib import Path


def test_autonomous_repair_publishes_only_a_draft_review_branch():
    workflow = (Path(__file__).resolve().parents[2] /
                ".github/workflows/bean-autonomous-selfrepair.yml").read_text(encoding="utf-8")
    assert 'git push origin HEAD:refs/heads/main' not in workflow
    assert 'git push origin "HEAD:refs/heads/$BRANCH"' in workflow
    assert "gh pr create --draft --base main" in workflow
    assert "candidate_verified_one_platform" in workflow
    assert "accepted_sha256" in workflow
    assert "all_tests_pass" in workflow
    assert "baseline_red" in workflow
