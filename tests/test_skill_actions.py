"""Native GoalCycle skill-action contract tests; no live model claims."""
import tempfile
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from bean.runtime.skill_actions import make_skill_actions


class SkillActionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.projects = {}
        for name in ("training", "holdout", "novel"):
            p = root / name
            (p / "tests").mkdir(parents=True)
            self.projects[name] = p
        self.kw = dict(projects=self.projects, vault=root / "vault",
                       journal=root / "journal.sqlite", output_root=root / "out",
                       provider=object())

    def test_rejects_untrusted_paths_and_invalid_goals(self):
        actions = make_skill_actions(**self.kw)
        self.assertEqual(actions["skill_acquire"]({"action_detail": {
            "capability": "skill_acquire", "name": "sample",
            "task": "Develop a real utility", "training": "/etc", "holdout": "holdout"
        }})["status"], "unknown")
        self.assertEqual(actions["skill_reuse"]({"action_detail": {
            "capability": "skill_reuse", "name": "../escape", "project": "novel"
        }})["status"], "unknown")

    def test_acquire_promotes_only_independently_verified_skill(self):
        actions = make_skill_actions(**self.kw)
        goal = {"action_detail": {"capability": "skill_acquire", "name": "sample",
                "task": "Implement a useful tested utility",
                "training": "training", "holdout": "holdout"}}
        with patch("bean.runtime.skill_actions.retrieve", side_effect=FileNotFoundError), \
             patch("bean.runtime.skill_actions.incubate_skill", return_value={
                 "skill_promotion_ready": False, "skill_origin": "fixture"
             }), patch("bean.runtime.skill_actions.promote") as promote:
            self.assertEqual(actions["skill_acquire"](goal)["status"], "failed")
            promote.assert_not_called()
        with patch("bean.runtime.skill_actions.retrieve", side_effect=FileNotFoundError), \
             patch("bean.runtime.skill_actions.incubate_skill", return_value={
                 "skill_promotion_ready": True, "accepted_source": "a" * 64,
                 "retained_skill": {"source_sha256": "a" * 64}
             }), patch("bean.runtime.skill_actions.promote", return_value={
                 "source_sha256": "a" * 64, "receipt_sha256": "b" * 64
             }) as promote:
            result = actions["skill_acquire"](goal)
            self.assertEqual(result["status"], "success")
            promote.assert_called_once()

    def test_reuse_requires_novel_test_set_and_no_model(self):
        actions = make_skill_actions(**self.kw)
        goal = {"action_detail": {"capability": "skill_reuse",
                                  "name": "sample", "project": "novel"}}
        receipt = {"passed": True, "independent_from_promotion_holdout": False,
                   "source_sha256": "a" * 64, "reuse_tests_sha256": "b" * 64}
        source = "def useful():\n    return 42\n"
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        archived = {"objective": "c" * 64, "source_sha256": digest}
        with patch("bean.runtime.skill_actions.retrieve", return_value=archived), \
             patch("bean.runtime.skill_actions.retrieve_verified_skill", return_value=source), \
             patch("bean.runtime.skill_actions.reuse", return_value=receipt):
            self.assertEqual(actions["skill_reuse"](goal)["status"], "failed")
            receipt["independent_from_promotion_holdout"] = True
            result = actions["skill_reuse"](goal)
            self.assertEqual(result["status"], "success")
            self.assertFalse(result["provider_invoked"])
        with patch("bean.runtime.skill_actions.retrieve", return_value=archived), \
             patch("bean.runtime.skill_actions.retrieve_verified_skill", return_value="tampered"), \
             patch("bean.runtime.skill_actions.reuse") as reuse:
            self.assertEqual(actions["skill_reuse"](goal)["reason"], "sqlite_vault_sha_mismatch")
            reuse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
