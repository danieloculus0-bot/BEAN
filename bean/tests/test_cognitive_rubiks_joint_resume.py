"""Check BEAN frozen cube continuation, exact weights and tamper detection."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from experiments.cognitive_gauntlet import rubiks3
from experiments.cognitive_gauntlet.rubiks3_joint_rescue import experiment
from experiments.cognitive_gauntlet.rubiks3_joint_resume import resume_receipt, verify_resume
from experiments.cognitive_gauntlet.rubiks3_sponge import _digest


class JointResumeTests(unittest.TestCase):
    def original(self, path):
        return experiment(train_seeds=range(3), test_seeds=range(31000, 31002),
                          train_lengths=(2, 3), test_lengths=(3, 20),
                          epochs=1, work_budget=1, rescue_backup=True, output=path)

    def test_replay_original_untouched_and_solver_isolation(self):
        with TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "source.json", Path(tmp) / "resume.json"
            old = self.original(source)
            raw = source.read_bytes()
            with patch.object(rubiks3, "solve", side_effect=AssertionError("solver called")):
                result = resume_receipt(source, slices=3, work_budget=2, output=target)
            self.assertEqual(source.read_bytes(), raw)
            self.assertTrue(verify_resume(source, target)["verified"])
            self.assertEqual(result["solved_before"], old["candidate_solved"])
            self.assertEqual(result["eligible_cases"] + result["excluded_count"], 4)
            for row in result["cases"]:
                self.assertEqual(row["resumed_solved"],
                                 rubiks3.apply(row["state"], row["resumed_moves"]) == rubiks3.SOLVED)
                self.assertEqual(row["resumed_moves"][:len(row["original_moves"])],
                                 row["original_moves"])

    def test_forged_result_and_bad_budgets_rejected(self):
        with TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "source.json", Path(tmp) / "resume.json"
            self.original(source)
            resume_receipt(source, slices=1, work_budget=1, output=target)
            forged = json.loads(target.read_text(encoding="utf-8"))
            forged["cases"][0]["resumed_solved"] = not forged["cases"][0]["resumed_solved"]
            forged["sha256"] = _digest({k: v for k, v in forged.items() if k != "sha256"})
            target.write_text(json.dumps(forged), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_resume(source, target)
            with self.assertRaises(ValueError):
                resume_receipt(source, slices=0)
            with self.assertRaises(ValueError):
                resume_receipt(source, work_budget=0)

    def test_frozen_weight_digest_mismatch_rejected(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.json"
            self.original(source)
            old = json.loads(source.read_text(encoding="utf-8"))
            old["initial_q_sha256"] = "0" * 64
            for row in old["cases"]:
                if row["candidate_checkpoint"] is not None:
                    row["candidate_checkpoint"]["full_q_sha256"] = "0" * 64
            old["sha256"] = _digest({k: v for k, v in old.items() if k != "sha256"})
            source.write_text(json.dumps(old), encoding="utf-8")
            with self.assertRaises(ValueError):
                resume_receipt(source)


if __name__ == "__main__":
    unittest.main()
