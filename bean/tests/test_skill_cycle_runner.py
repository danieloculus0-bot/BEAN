"""Cross-process acceptance for the native skill-cycle CLI.

The writer below is a deterministic fixture, NOT a real model. The production
CLI refuses synthetic provider selection and requires explicit Ollama/OpenRouter.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

from bean.runtime.skill_cycle_runner import execute_phase


class FixtureWriter:
    def propose(self, task, original, history, iteration):
        return "def solve(value):\n    return value * 2\n"


def project(root, number):
    (root / "bean" / "skills").mkdir(parents=True)
    (root / "bean" / "__init__.py").write_text("")
    (root / "bean" / "skills" / "__init__.py").write_text("")
    (root / "tests").mkdir()
    (root / "tests" / "test_skill.py").write_text(
        "import unittest\nfrom bean.skills.double_value import solve\n"
        "class Check(unittest.TestCase):\n"
        f"    def test_value(self): self.assertEqual(solve({number}), {number * 2})\n"
    )


def test_native_acquire_then_reuse_in_separate_interpreter(tmp_path):
    projects = {}
    for key, number in (("training", 3), ("holdout", -11), ("novel", 29)):
        path = tmp_path / key
        project(path, number)
        projects[key] = str(path)
    config = {
        "database": str(tmp_path / "core.sqlite"),
        "projects": projects, "vault": str(tmp_path / "vault"),
        "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"),
        "plan_id": "cross-process-acceptance",
        "name": "double_value",
        "task": "Create a reusable integer doubling function for signed integers",
        "training": "training", "holdout": "holdout", "novel": "novel",
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    first = execute_phase(config, phase="acquire", provider=FixtureWriter())
    assert first["status"] == "success", first
    assert first["plan"]["steps"][1]["status"] == "pending"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    child = subprocess.run(
        [sys.executable, "-m", "bean.runtime.skill_cycle_runner",
         "--config", str(config_path), "--phase", "reuse"],
        env=env, capture_output=True, text=True, timeout=45,
    )
    assert child.returncode == 0, child.stdout + child.stderr
    second = json.loads(child.stdout)
    assert second["status"] == "success"
    assert second["evaluation_seal_sha256"] == first["evaluation_seal_sha256"]
    assert second["result"]["provider_invoked"] is False
    assert second["result"]["new_test_set"] is True
    assert second["result"]["passed"] is True
    assert second["result"]["source_sha256"] == first["result"]["source_sha256"]
    assert second["plan"]["status"] == "completed"
    assert second["independent_external_verdict_recorded"] is False
    again = subprocess.run(
        [sys.executable, "-m", "bean.runtime.skill_cycle_runner",
         "--config", str(config_path), "--phase", "reuse"],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert again.returncode != 0
    assert "reuse already attempted" in again.stderr


def test_reuse_rejects_changed_withheld_evaluation(tmp_path):
    projects = {}
    for key, number in (("training", 3), ("holdout", -11), ("novel", 29)):
        path = tmp_path / key
        project(path, number)
        projects[key] = str(path)
    config = {
        "database": str(tmp_path / "core.sqlite"),
        "projects": projects, "vault": str(tmp_path / "vault"),
        "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"),
        "plan_id": "sealed-evaluation",
        "name": "double_value",
        "task": "Create a reusable integer doubling function for signed integers",
        "training": "training", "holdout": "holdout", "novel": "novel",
    }
    acquired = execute_phase(config, phase="acquire", provider=FixtureWriter())
    assert acquired["status"] == "success"
    withheld = Path(projects["novel"]) / "tests" / "test_skill.py"
    withheld.write_text(withheld.read_text() + "\\n# changed after acquisition\\n")
    import pytest
    with pytest.raises(ValueError, match="evaluation project seal mismatch"):
        execute_phase(config, phase="reuse")
