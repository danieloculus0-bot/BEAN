"""Offline regression for BEAN's independently verified SQLite skill store."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from bean.optimization.skill_incubator import persist_verified_skill, retrieve_verified_skill


class VerifiedSkillStoreTests(unittest.TestCase):
    def test_restart_reuse_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "skills.sqlite3"
            source = "def square(x):\n    return x * x\n"
            candidate = root / "square.py"
            candidate.write_text(source, encoding="utf-8")
            sha = hashlib.sha256(source.encode()).hexdigest()
            objective = "a" * 64
            receipt = persist_verified_skill(db, name="square",
                                             source_path=candidate,
                                             source_sha256=sha, objective=objective)
            self.assertFalse(receipt["installed_into_core"])
            candidate.unlink()
            recovered = retrieve_verified_skill(db, name="square", objective=objective)
            scope = {}
            exec(compile(recovered, "<recovered-skill>", "exec"), scope)
            self.assertEqual(scope["square"](7), 49)
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE verified_skills SET source=? WHERE name=?",
                                   ("def square(x): return 999", "square"))
            with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                retrieve_verified_skill(db, name="square", objective=objective)

    def test_reject_unverified_source_and_conflicting_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "skill.py"
            candidate.write_text("def f(): return 1\n", encoding="utf-8")
            db = root / "skills.sqlite3"
            with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                persist_verified_skill(db, name="skill", source_path=candidate,
                                       source_sha256="0" * 64, objective="b" * 64)
            sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            persist_verified_skill(db, name="skill", source_path=candidate,
                                   source_sha256=sha, objective="b" * 64)
            candidate.write_text("def f(): return 2\n", encoding="utf-8")
            sha2 = hashlib.sha256(candidate.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "conflicts"):
                persist_verified_skill(db, name="skill", source_path=candidate,
                                       source_sha256=sha2, objective="b" * 64)


if __name__ == "__main__":
    unittest.main()
