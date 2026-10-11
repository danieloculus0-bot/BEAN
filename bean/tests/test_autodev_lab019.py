"""Lab019: actual source-writing, immutable tests, restart and journal falsification."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from unittest.mock import patch
import pytest

from bean.optimization.autodev import (
    ASTBruteForce, ModelWriter, Journal, evaluate, run_cycle, target_file,
)

PROJECT = Path(__file__).resolve().parents[2] / "experiments" / "autodev" / "seed_project"
TARGET = "bean/skills/clip_score.py"
TASK = "Repair score clipping so values never exceed 100 or fall below zero"


def config(tmp_path, attempts=25):
    return dict(project=PROJECT, target=TARGET, task=TASK,
                journal_path=tmp_path / "learning.sqlite",
                output=tmp_path / "proposals",
                provider=ASTBruteForce((PROJECT / TARGET).read_text(encoding="utf-8")),
                attempts=attempts)


def test_generated_source_really_changes_and_passes_frozen_tests(tmp_path):
    original = (PROJECT / TARGET).read_bytes()
    result = run_cycle(**config(tmp_path))
    assert result["status"] == "validated_patch_written"
    assert result["baseline"]["test_count"] == 7 and not result["baseline"]["passed"]
    assert result["new_attempts"] == 7
    assert result["accepted_iteration"] == 6
    rewritten = Path(result["validated_path"]).read_text(encoding="utf-8")
    assert "min(score, 100)" in rewritten
    assert evaluate(PROJECT, TARGET, rewritten)["passed"]
    assert (PROJECT / TARGET).read_bytes() == original
    with sqlite3.connect(tmp_path / "learning.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 7
    report = json.loads((tmp_path / "proposals" / "journal-export.json").read_text())
    assert report["attempts"] == 7
    assert len(report["tip"]) == 64
    assert len(list((tmp_path / "proposals" / "candidates").rglob("*.py"))) == 7


def test_restart_preserves_success_without_repeating_search(tmp_path):
    first = run_cycle(**config(tmp_path))
    second = run_cycle(**config(tmp_path))
    assert second["status"] == "previously_validated_in_memory"
    assert second["prior_attempts"] == 7
    assert second["new_attempts"] == 0
    assert second["accepted_source"] == first["accepted_source"]


def test_brute_force_search_can_resume_after_failures(tmp_path):
    first = run_cycle(**config(tmp_path, attempts=2))
    assert first["status"] == "unresolved"
    assert first["new_attempts"] == 2
    assert "min(score, 101)" in (PROJECT / TARGET).read_text()
    result = run_cycle(**config(tmp_path, attempts=20))
    assert result["status"] == "validated_patch_written"
    assert result["prior_attempts"] == 2
    assert result["new_attempts"] == 5


def test_historical_tampering_is_detected(tmp_path):
    run_cycle(**config(tmp_path, attempts=1))
    path = tmp_path / "learning.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("UPDATE attempts SET payload=? WHERE id=1", ('{}',))
    with pytest.raises((ValueError, KeyError)):
        Journal(path)


def test_target_path_traversal_and_symlink_are_refused(tmp_path):
    for path in ("../secret.py", "bean/__init__.py", "bean/skills/missing.py"):
        with pytest.raises(ValueError):
            target_file(PROJECT, path)
    alias = tmp_path / "linked"
    alias.symlink_to(PROJECT, target_is_directory=True)
    with pytest.raises(ValueError):
        target_file(alias, TARGET)


def test_ollama_source_generation_contract_with_mocked_provider():
    calls = []

    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self, maximum):
            return json.dumps({"response": "def answer():\n    return 42"}).encode()

    def fake(request, timeout):
        calls.append(request)
        return Reply()

    with patch("urllib.request.urlopen", side_effect=fake):
        written = ModelWriter("ollama", "qwen2.5-coder:7b").propose(
            "Fix a witnessed bug", "def answer(): return 0", [], 0)
    assert written == "def answer():\n    return 42\n"
    body = json.loads(calls[0].data)
    assert body["stream"] is False
    assert "Fix a witnessed bug" in body["prompt"]


def test_openrouter_requires_real_provider_key_not_fake_result(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        ModelWriter("openrouter", "example/model").propose(
            "Fix independent failure", "def a(): return 0", [], 0)


def test_modified_test_suite_creates_separate_objective(tmp_path):
    project = tmp_path / "independent"
    import shutil
    shutil.copytree(PROJECT, project)
    first = run_cycle(project=project, target=TARGET, task=TASK,
                      journal_path=tmp_path / "journal.sqlite",
                      output=tmp_path / "out",
                      provider=ASTBruteForce((project / TARGET).read_text()), attempts=2)
    path = project / "tests" / "test_clip_score.py"
    path.write_text(path.read_text() + "\n# test suite version 2\n")
    second = run_cycle(project=project, target=TARGET, task=TASK,
                       journal_path=tmp_path / "journal.sqlite",
                       output=tmp_path / "out",
                       provider=ASTBruteForce((project / TARGET).read_text()), attempts=2)
    assert first["objective"] != second["objective"]
    assert second["prior_attempts"] == 0
