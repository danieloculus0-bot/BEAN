"""Executable native GoalCycle acquire, persist, reboot and reuse acceptance.

The fixture writer is NOT a live model or general-intelligence benchmark.
This test proves the same canonical GoalCycle and skill vault can complete a
real code-evaluation workflow across two Python interpreters and distinct tests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine,
)
from bean.memory.session import begin_session
from bean.memory.store import get_store, init_store
from bean.runtime.goal_cycle import GoalCycle
from bean.runtime.skill_actions import make_skill_actions


class FixtureWriter:
    calls = 0

    def propose(self, task, original, history, iteration):
        self.calls += 1
        return "def solve(value):\n    return value * 2\n"


class SkillPlanIntegration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "bean.sqlite"
        init_store(str(self.database))
        self.addCleanup(lambda: get_store().close())
        self.session = begin_session()
        self.plan_id = "skill-learning-" + uuid.uuid4().hex
        self.projects = {
            name: self.make_project(name, value)
            for name, value in (("training", 3), ("holdout", 11), ("novel", 29))
        }
        self.vault = self.root / "vault"
        self.journal = self.root / "lab019.sqlite"
        self.output = self.root / "output"

    def make_project(self, name, value):
        project = self.root / name
        (project / "bean" / "skills").mkdir(parents=True)
        (project / "bean" / "__init__.py").write_text("", encoding="utf-8")
        (project / "bean" / "skills" / "__init__.py").write_text("", encoding="utf-8")
        (project / "tests").mkdir()
        (project / "tests" / "test_case.py").write_text(
            "import unittest\n"
            "from bean.skills.double_value import solve\n"
            "class TestCase(unittest.TestCase):\n"
            "    def test_value(self):\n"
            "        self.assertEqual(solve(" + str(value) + "), "
            + str(value * 2) + ")\n",
            encoding="utf-8",
        )
        return project

    def actions(self, provider):
        return make_skill_actions(
            projects=self.projects, vault=self.vault, journal=self.journal,
            output_root=self.output, provider=provider, attempts=2,
        )

    def test_native_ordered_plan_acquires_then_reuses_after_process_restart(self):
        acquisition = GoalProposal(
            "learn_reusable_skill", ActionType.RUN_EXPERIMENT,
            "Create tested skill from unknown executable objective", 2,
            ApprovalRequired.NONE,
            {"capability": "skill_acquire", "name": "double_value",
             "task": "Create a reusable integer doubling function",
             "training": "training", "holdout": "holdout"},
            "curiosity",
        )
        retrieval = GoalProposal(
            "apply_retained_skill", ActionType.RUN_EXPERIMENT,
            "Apply retained code to independently withheld inputs", 2,
            ApprovalRequired.NONE,
            {"capability": "skill_reuse", "name": "double_value", "project": "novel"},
            "curiosity",
        )
        plan = GoalStateEngine().propose_plan(
            self.session, self.plan_id, [acquisition, retrieval],
        )
        self.assertEqual(len(plan), 2)
        writer = FixtureWriter()
        goal_cycle = GoalCycle({"run_experiment": self.actions(writer)["run_experiment"]})
        first = goal_cycle.poll_due(max_goals=1)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["status"], "success", first)
        self.assertEqual(writer.calls, 1)
        self.assertEqual(goal_cycle.plan_status(self.plan_id)["status"], "pending")
        self.assertEqual(
            [step["status"] for step in goal_cycle.plan_status(self.plan_id)["steps"]],
            ["completed", "pending"],
        )

        # Restart in a different Python interpreter. The provider is absent:
        # no model call can create a second candidate during reuse.
        script = (
            "import json,sys\n"
            "from pathlib import Path\n"
            "from bean.memory.store import init_store\n"
            "from bean.runtime.goal_cycle import GoalCycle\n"
            "from bean.runtime.skill_actions import make_skill_actions\n"
            "root=Path(sys.argv[1])\n"
            "init_store(str(root/'bean.sqlite'))\n"
            "projects={n:root/n for n in ('training','holdout','novel')}\n"
            "actions=make_skill_actions(projects=projects,vault=root/'vault',"
            "journal=root/'lab019.sqlite',output_root=root/'output',provider=None)\n"
            "cycle=GoalCycle({'run_experiment':actions['run_experiment']})\n"
            "print(json.dumps({'runs':cycle.poll_due(max_goals=1),"
            "'plan':cycle.plan_status(sys.argv[2]),'history':cycle.history()}))\n"
        )
        env = {
            **os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        }
        child = subprocess.run(
            [sys.executable, "-c", script, str(self.root), self.plan_id],
            capture_output=True, text=True, timeout=35, env=env,
        )
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        result = json.loads(child.stdout)
        self.assertEqual([r["status"] for r in result["runs"]], ["success"])
        self.assertEqual(result["plan"]["status"], "completed")
        self.assertEqual([step["status"] for step in result["plan"]["steps"]],
                         ["completed", "completed"])
        # Both outcomes are recorded in the same canonical persistent goal DB.
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual({run["state"] for run in result["history"]}, {"success"})
        reused = next(run for run in result["history"]
                      if json.loads(run["result_json"]).get("provider_invoked") is False)
        reused_result = json.loads(reused["result_json"])
        self.assertTrue(reused_result["new_test_set"])
        self.assertTrue(reused_result["passed"])

    def test_malformed_plan_metadata_cannot_bypass_handler(self):
        handler = self.actions(FixtureWriter())["run_experiment"]
        malformed = {"proposal_id": "not-its-stable-id", "action_detail": {
            "capability": "skill_acquire", "name": "double_value",
            "task": "Create a reusable integer doubling function",
            "training": "training", "holdout": "holdout",
            "goal_plan": {"schema": "bean.goal.plan.v1", "id": "stable",
                          "step": 0, "steps": 2},
        }}
        self.assertEqual(handler(malformed)["status"], "unknown")
        self.assertFalse(self.vault.exists())

    def test_unrelated_experiments_keep_existing_fallback(self):
        existing = lambda goal: {"status": "success", "source": "original_handler"}
        actions = make_skill_actions(
            projects=self.projects, vault=self.vault, journal=self.journal,
            output_root=self.output, provider=FixtureWriter(), fallback=existing,
        )
        self.assertEqual(actions["run_experiment"](
            {"action_detail": {"capability": "native_reason_local"}}),
            {"status": "success", "source": "original_handler"},
        )


if __name__ == "__main__":
    unittest.main()
