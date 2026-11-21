"""Fail-closed acceptance for the real-model experiment entry point."""
import json
from pathlib import Path

import pytest

from bean.runtime.skill_cycle_live_experiment import run_experiment


def test_missing_control_rejected_before_any_model_execution(tmp_path):
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(ValueError, match="all four control arms required"):
        run_experiment(config=config, provider="ollama", model="qwen2.5:1.5b",
                       controls={}, receipt=tmp_path / "receipt.json")
    assert not (tmp_path / "receipt.json").exists()


def test_model_required_before_side_effects(tmp_path):
    with pytest.raises(ValueError, match="real model provider"):
        run_experiment(config=tmp_path / "absent.json", provider="ollama",
                       model="", controls={}, receipt=tmp_path / "receipt.json")


def test_failed_acquisition_persists_negative_receipt_without_reuse(tmp_path):
    # The runner fingerprints the novel project before attempting model acquisition.
    # Keep that project present so this test reaches the intended acquisition failure.
    (tmp_path / "novel").mkdir()
    (tmp_path / "novel" / "test_case.py").write_text("assert True\n")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "database": str(tmp_path / "db.sqlite"),
        "projects": {"training": str(tmp_path / "training"),
                     "holdout": str(tmp_path / "holdout"),
                     "novel": str(tmp_path / "novel")},
        "vault": str(tmp_path / "vault"),
        "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"),
        "plan_id": "negative-experiment",
        "name": "skill", "task": "Solve a task",
        "training": "training", "holdout": "holdout", "novel": "novel",
    }))
    controls = {}
    for arm in ("frozen", "no_memory", "grammar_matched", "strong"):
        path = tmp_path / (arm + ".py")
        path.write_text("def solve(x): return x\n")
        controls[arm] = path
    receipt = tmp_path / "receipt.json"
    result = run_experiment(config=config, provider="ollama",
                            model="not-installed-local-model",
                            controls=controls, receipt=receipt)
    assert result["completed"] is False
    assert "acquire" in result["phases"]
    assert "reuse" not in result["phases"]
    assert result["independent_external_verdict_recorded"] is False
    assert json.loads(receipt.read_text()) == result

def test_failed_novel_candidate_does_not_mark_experiment_complete(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from bean.runtime import skill_cycle_live_experiment as live
    from bean.runtime import skill_cycle_controls
    projects = {}
    for name in ("training", "holdout", "novel"):
        root = tmp_path / name
        root.mkdir()
        (root / "test_case.py").write_text("assert True\\n")
        projects[name] = str(root)
    settings = {
        "database": str(tmp_path / "db.sqlite"), "projects": projects,
        "vault": str(tmp_path / "vault"), "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"), "plan_id": "fail-closed",
        "name": "skill", "task": "Solve a withheld engineering task",
        "training": "training", "holdout": "holdout", "novel": "novel",
    }
    config = tmp_path / "config.json"
    config.write_text(json.dumps(settings))
    controls = {}
    for arm in live.ARMS:
        source = tmp_path / (arm + ".py")
        source.write_text("def solve(x): return x\\n")
        controls[arm] = source
    def native_phase(command, **kwargs):
        phase = command[command.index("--phase") + 1]
        receipt = {
            "schema": "bean.native_skill_cycle.runner.v1",
            "phase": phase, "plan_id": settings["plan_id"],
            "status": "success", "run_id": phase + "-run",
            "result_sha256": "abc123", "evaluation_seal_sha256": "sealed",
            "provider_available": phase == "acquire",
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(receipt), stderr="")
    monkeypatch.setattr(live.subprocess, "run", native_phase)
    monkeypatch.setattr(skill_cycle_controls, "compare", lambda **kwargs: {
        "outcomes": {"candidate": {"passed": False, "test_count": 2},
                     **{arm: {"passed": True, "test_count": 2} for arm in live.ARMS}},
    })
    receipt = tmp_path / "receipt.json"
    result = live.run_experiment(config=config, provider="ollama", model="local-model",
                                 controls=controls, receipt=receipt)
    assert result["completed"] is False
    assert result["comparison_error"] == "retained candidate failed independent novel evaluation"
    assert json.loads(receipt.read_text()) == result


def test_zero_exit_forged_native_receipt_never_reaches_comparison(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from bean.runtime import skill_cycle_live_experiment as live
    projects = {}
    for name in ("training", "holdout", "novel"):
        root = tmp_path / name
        root.mkdir()
        (root / "case.py").write_text("pass\\n")
        projects[name] = str(root)
    settings = {
        "database": str(tmp_path / "db.sqlite"), "projects": projects,
        "vault": str(tmp_path / "vault"), "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"), "plan_id": "forged-run",
        "name": "skill", "task": "Solve an unfamiliar task",
        "training": "training", "holdout": "holdout", "novel": "novel",
    }
    config = tmp_path / "config.json"
    config.write_text(json.dumps(settings))
    controls = {}
    for arm in live.ARMS:
        path = tmp_path / (arm + ".py")
        path.write_text("def solve(x): return x\\n")
        controls[arm] = path
    monkeypatch.setattr(live.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout='{"status":"success"}', stderr=""))
    receipt = tmp_path / "receipt.json"
    result = live.run_experiment(config=config, provider="ollama",
                                 model="qwen2.5:1.5b", controls=controls, receipt=receipt)
    assert result["completed"] is False
    assert result["phases"]["acquire"]["verification_error"] == "invalid native GoalCycle phase provenance"
    assert "reuse" not in result["phases"]
    assert "comparison" not in result
    assert json.loads(receipt.read_text()) == result


@pytest.mark.parametrize("outcomes,expected", [
    ({}, "incomplete five-arm outcome matrix"),
    (None, "incomplete five-arm outcome matrix"),
    ({"candidate": {"passed": True, "test_count": 2}}, "incomplete five-arm outcome matrix"),
    ({"candidate": {"passed": True, "test_count": 2},
      "frozen": {"passed": False, "test_count": 1},
      "no_memory": {"passed": False, "test_count": 2},
      "grammar_matched": {"passed": False, "test_count": 2},
      "strong": {"passed": False, "test_count": 2}}, "five arms did not execute identical test counts"),
])
def test_comparison_rejects_incomplete_or_unequal_outcomes(tmp_path, monkeypatch, outcomes, expected):
    from types import SimpleNamespace
    from bean.runtime import skill_cycle_live_experiment as live
    from bean.runtime import skill_cycle_controls
    projects = {}
    for name in ("training", "holdout", "novel"):
        root = tmp_path / name
        root.mkdir()
        (root / "case.py").write_text("pass\\n")
        projects[name] = str(root)
    settings = {
        "database": str(tmp_path / "db.sqlite"), "projects": projects,
        "vault": str(tmp_path / "vault"), "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"), "plan_id": "parity-check",
        "name": "skill", "task": "Evaluate an unfamiliar skill",
        "training": "training", "holdout": "holdout", "novel": "novel",
    }
    config = tmp_path / "config.json"
    config.write_text(json.dumps(settings))
    controls = {}
    for arm in live.ARMS:
        source = tmp_path / (arm + ".py")
        source.write_text("def solve(x): return x\\n")
        controls[arm] = source
    def native_phase(command, **kwargs):
        phase = command[command.index("--phase") + 1]
        native = {
            "schema": "bean.native_skill_cycle.runner.v1",
            "phase": phase, "plan_id": settings["plan_id"],
            "status": "success", "run_id": phase + "-unique",
            "result_sha256": "abc123", "evaluation_seal_sha256": "sealed",
            "provider_available": phase == "acquire",
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(native), stderr="")
    monkeypatch.setattr(live.subprocess, "run", native_phase)
    monkeypatch.setattr(skill_cycle_controls, "compare", lambda **kwargs: {"outcomes": outcomes})
    receipt = tmp_path / "receipt.json"
    result = live.run_experiment(config=config, provider="ollama", model="fixture-only",
                                 controls=controls, receipt=receipt)
    assert result["completed"] is False
    assert result["comparison_error"] == expected
    assert json.loads(receipt.read_text()) == result
