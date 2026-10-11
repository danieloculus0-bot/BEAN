"""Lab024 tests are deliberately MOCK protocol checks, never scored AI results."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from experiments.agent_arena import local_duel_lab024 as duel
from experiments.agent_arena.cases import CASES


class FakeModel:
    model = "fictional-local-coder"
    route = "ollama/fictional-local-coder"
    def preflight(self):
        return {"ready": True}


def fake_bean(client, spec, previous, score, n):
    assert spec["source"] in (spec["source"],)
    return (spec["source"] + "\n# synthetic_bean_round" + str(n) + "\n", {
        "status": "candidate_drafted_not_tested", "model_requested": client.route,
        "model_served": [client.route], "request_count": 1,
    })


def fake_aider(client, spec, previous, score, n):
    return (spec["source"] + "\n# synthetic_aider_round" + str(n) + "\n", {
        "status": "candidate_drafted_not_tested", "model_requested": client.route,
        "model_served": [client.route], "request_count": 1,
    })


def fake_dev(source, name):
    assert name in duel.DEVELOPMENT
    p = 3 if "bean_round3" in source else 2 if "bean_round2" in source else 1
    return {"status": "failed", "passed": p, "total": 3,
            "isolation": "explicit_mock_not_executed"}


def fake_holdout(source, test):
    passed = 8 if "bean_round3" in source else (
        4 if "aider_round" in source else 0
    )
    return {"status": "passed" if passed == 8 else "failed",
            "passed_tests": passed, "total_tests": 8}


def test_journal_reopens_and_uses_best_development_round_not_hidden(tmp_path):
    root = tmp_path / "rounds"
    receipts = duel.author(root, client=FakeModel(), bean_writer=fake_bean,
                           aider_writer=fake_aider, scorer=fake_dev)
    assert len(receipts["cases"]) == len(CASES)
    assert all(receipts["cases"][case]["bean"]["selected_round"] == 3
               for case in CASES)
    assert all(receipts["cases"][case]["aider"]["selected_round"] == 1
               for case in CASES)
    result = duel.judge(root, grader=fake_holdout)
    assert result["classification"] == "BEAN_WIN"
    assert result["comparable"]
    assert result["scores"]["bean"]["holdout_passed"] == 16
    assert result["scores"]["aider"]["holdout_passed"] == 8
    assert result["rounds_per_agent"] == 3


def test_refuse_mutated_author_candidate(tmp_path):
    root = tmp_path / "challenge"
    duel.author(root, client=FakeModel(), bean_writer=fake_bean,
                aider_writer=fake_aider, scorer=fake_dev)
    selected = root / "candidates" / next(iter(CASES)) / "bean" / "round3.py"
    selected.write_text("def altered(): pass\n")
    with pytest.raises(ValueError, match="modified since author receipt"):
        duel.judge(root, grader=fake_holdout)


def test_missing_agent_is_not_promoted_to_a_bean_win(tmp_path):
    root = tmp_path / "missing"
    def failed_aider(client, spec, previous, score, n):
        return None, {"status": "tool_or_transport_failure",
                      "model_requested": client.route,
                      "model_served": [], "reason": "fixture_missing"}
    duel.author(root, client=FakeModel(), bean_writer=fake_bean,
                aider_writer=failed_aider, scorer=fake_dev)
    result = duel.judge(root, grader=fake_holdout)
    assert result["classification"] == "INCONCLUSIVE"
    assert not result["comparable"]


def test_missing_real_docker_is_not_a_development_zero(tmp_path):
    def no_docker(command, **kwargs):
        raise FileNotFoundError("docker")
    score = duel.development_score("def replay(events, as_of): return {}\n",
                                   "ledger_revisions", runner=no_docker)
    assert score["status"] == "infrastructure_failure"


def test_docker_dev_does_not_accept_any_network_or_secrets():
    invoked = []
    def mock_runner(command, **kwargs):
        invoked.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1, stdout="",
                    stderr="Ran 3 tests in 0.01s\nFAILED (failures=1)")
    row = duel.development_score("def can_access(*args): return False\n",
                                 "permission_graph", runner=mock_runner)
    assert row["passed"] == 2 and row["total"] == 3
    command, opts = invoked[0]
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--read-only")] == "--read-only"
    assert command[command.index("--user") + 1] == "65534:65534"
    assert "OPENROUTER_API_KEY" not in opts["env"]
    assert "GITHUB_TOKEN" not in opts["env"]
    assert "--cap-drop" in command


def test_do_not_mix_trials(tmp_path):
    root = tmp_path / "old"
    root.mkdir()
    (root / "receipt").write_text("old")
    with pytest.raises(ValueError, match="fresh output"):
        duel.author(root, client=FakeModel(), bean_writer=fake_bean,
                    aider_writer=fake_aider, scorer=fake_dev)


def test_model_failure_not_a_successful_source(tmp_path):
    root = tmp_path / "absent"
    def no_bean(client, spec, previous, score, n):
        return None, {"status": "invalid_candidate",
                      "model_requested": client.route,
                      "model_served": [client.route]}
    duel.author(root, client=FakeModel(), bean_writer=no_bean,
                aider_writer=fake_aider, scorer=fake_dev)
    verdict = duel.judge(root, grader=fake_holdout)
    assert verdict["classification"] == "INCONCLUSIVE"
