"""Retained skill discovery and nonempty replay acceptance."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from bean.optimization.skill_incubator import (
    evaluate_retained_skill, list_retained_skills, persist_verified_skill,
)


class RetainedSkillDiscoveryTests(unittest.TestCase):
    def test_discover_and_replay_after_reopening_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "skills.sqlite"
            self.assertEqual(list_retained_skills(db, name="double"), [])
            self.assertFalse(db.exists())
            source = "def double(x):\n    return x * 2\n"
            file = root / "double.py"
            file.write_text(source, encoding="utf-8")
            objective = "a" * 64
            sha = hashlib.sha256(source.encode()).hexdigest()
            persist_verified_skill(db, name="double", source_path=file,
                                   source_sha256=sha, objective=objective)
            self.assertEqual(list_retained_skills(db, name="double"), [
                {"name": "double", "objective_sha256": objective, "source_sha256": sha}])
            project = root / "transfer"
            (project / "tests").mkdir(parents=True)
            empty = evaluate_retained_skill(db, name="double", objective=objective,
                                            evaluation_project=project)
            self.assertFalse(empty["passed"])
            self.assertEqual(empty["test_count"], 0)
            (project / "tests" / "test_transfer.py").write_text(
                "import unittest\nfrom bean.skills.double import double\n"
                "class Transfer(unittest.TestCase):\n"
                "    def test_new(self): self.assertEqual(double(-7), -14)\n",
                encoding="utf-8")
            result = evaluate_retained_skill(db, name="double", objective=objective,
                                             evaluation_project=project)
            self.assertTrue(result["passed"], result)
            self.assertEqual(result["test_count"], 1)
            self.assertEqual(result["source_sha256"], sha)
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE verified_skills SET source='tampered'")
            with self.assertRaises(ValueError):
                list_retained_skills(db, name="double")


if __name__ == "__main__":
    unittest.main()
