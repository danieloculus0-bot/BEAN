"""Independent deterministic Sponge learning and persistence regression."""
import tempfile
import unittest
from pathlib import Path
from bean.optimization.sponge import Sponge


class SpongeTests(unittest.TestCase):
    def test_learns_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "learning.sqlite"
            sponge = Sponge(db, ("left", "right"), epsilon=0, alpha=.25)
            contexts = [{"signal": 0}, {"signal": 1}]
            # Alternate two contexts; correct action yields +1, wrong action -1.
            # Initial policy chooses left for both; learning must fix signal=1.
            baseline = sum(1 for c in contexts if sponge.choose(c, explore=False) == ("left" if c["signal"] == 0 else "right"))
            for _ in range(100):
                for c in contexts:
                    for action in ("left", "right"):
                        sponge.observe(c, action, 1 if action == ("left" if c["signal"] == 0 else "right") else -1)
            trained = sum(1 for c in contexts if sponge.choose(c, explore=False) == ("left" if c["signal"] == 0 else "right"))
            self.assertEqual(baseline, 1)
            self.assertEqual(trained, 2)
            tip = sponge.journal.export()["tip"]
            sponge.close()
            resumed = Sponge(db, ("left", "right"), epsilon=0, alpha=.25)
            self.assertEqual(resumed.journal.export()["tip"], tip)
            self.assertEqual(resumed.count, 400)
            self.assertEqual(resumed.choose({"signal": 1}, explore=False), "right")
            with self.assertRaises(ValueError):
                resumed.observe({"signal": 1}, "right", float("nan"))
            resumed.close()

    def test_rejects_incompatible_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "learning.sqlite"
            learner = Sponge(db, ("a", "b"))
            learner.observe("x", "a", 1)
            learner.close()
            with self.assertRaises(ValueError):
                Sponge(db, ("a", "c"))


if __name__ == "__main__":
    unittest.main()
