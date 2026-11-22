"""Regression: the persisted source survives deletion and a fresh interpreter."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bean.optimization.skill_incubator import persist_verified_skill


class RecoveryProcessTests(unittest.TestCase):
    def test_fresh_process_recovery_and_tamper_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "skills.sqlite"
            candidate = root / "candidate.py"
            source = "def shift(x):\n    return x + 3\n"
            candidate.write_text(source, encoding="utf-8")
            objective = "c" * 64
            sha = hashlib.sha256(source.encode()).hexdigest()
            persist_verified_skill(db, name="shift", source_path=candidate,
                                   source_sha256=sha, objective=objective)
            candidate.unlink()
            cmd = [sys.executable, "-m", "bean.optimization.skill_reuse",
                   "--database", str(db), "--name", "shift",
                   "--objective", objective]
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            recovered = json.loads(result.stdout)
            self.assertEqual(recovered["source"], source)
            self.assertEqual(recovered["source_sha256"], sha)
            self.assertFalse(recovered["executed"])
            self.assertFalse(recovered["independent_transfer_verified"])
            import sqlite3
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE verified_skills SET source = ?",
                             ("def shift(x): return -1",))
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
