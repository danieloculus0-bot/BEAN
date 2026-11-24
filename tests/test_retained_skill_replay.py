import hashlib
from pathlib import Path
import tempfile
import unittest

from bean.optimization.skill_incubator import (
    list_verified_skills, persist_verified_skill, replay_verified_skills,
)


class RetainedSkillReplayTest(unittest.TestCase):
    def test_replay_uses_persisted_source_and_reports_missing_and_failed_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "skills.sqlite"
            source = root / "source.py"
            source.write_text("def twice(n):\n    return n * 2\n", encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            objectives = {name: hashlib.sha256(name.encode()).hexdigest()
                          for name in ("double", "missing", "incorrect")}
            for name, objective in objectives.items():
                persist_verified_skill(db, name=name, source_path=source,
                                       source_sha256=digest, objective=objective)
            source.unlink()
            projects = {}
            for name, expected in (("double", 26), ("incorrect", 27)):
                project = root / name
                (project / "tests").mkdir(parents=True)
                (project / "bean" / "skills").mkdir(parents=True)
                (project / "bean" / "__init__.py").touch()
                (project / "bean" / "skills" / "__init__.py").touch()
                (project / "tests" / "test_transfer.py").write_text(
                    "import unittest\nfrom bean.skills." + name + " import twice\n"
                    "class Transfer(unittest.TestCase):\n"
                    "    def test_unseen(self):\n"
                    "        self.assertEqual(twice(13), " + str(expected) + ")\n",
                    encoding="utf-8")
                projects[(name, objectives[name])] = project
            self.assertEqual(len(list_verified_skills(db)), 3)
            result = replay_verified_skills(db, projects)
            self.assertEqual((result["passed"], result["failed"],
                              result["not_evaluated"], result["model_calls"]),
                             (1, 1, 1, 0))
            self.assertTrue(next(row for row in result["results"]
                                 if row["name"] == "double")["fresh_process"])
            self.assertEqual(len(list_verified_skills(db)), 3)


if __name__ == "__main__":
    unittest.main()
