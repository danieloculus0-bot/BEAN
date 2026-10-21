"""Exactly measured synthetic compression with BEAN Core Q-learning receipts."""
import base64
import tempfile
from pathlib import Path
import unittest

from bean.optimization.information_balloon import unpack,digest
from bean.optimization.information_balloon_q import (
    APP,CHOICES,evaluate,make_case,measure_case,run_learning)
from bean.optimization.portfolio_ledger import PortfolioLedger


class InformationBalloonQTests(unittest.TestCase):
    def test_all_codecs_restore_binary_exactness_or_reject_budget(self):
        case=make_case(7,22)
        for action in CHOICES:
            with self.subTest(action=action):
                score=measure_case(case,action)
                self.assertEqual(score["source_sha256"],digest(case["raw"]))
                self.assertEqual(unpack(score["package"]),case["raw"])
                self.assertEqual(score["reference_recall"],1.0)
                self.assertGreater(score["compression_ratio"],0)
                self.assertLess(score["reward"],1e4)
                if not score["fits"]:
                    self.assertLess(score["reward"],0)

    def test_q_episode_count_independent_holdout_and_exact_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/"compression_q.sqlite"
            report,trials=run_learning(
                db,episodes=55,train_seed=101,
                validation_seed=202,holdout_seed=303,eval_cases=10)
            self.assertEqual(report["episodes"],55)
            self.assertEqual(report["q_updates"],55)
            self.assertEqual(report["ledger_verification"]["events"],55)
            self.assertEqual(len(trials),55)
            self.assertEqual(report["independent_holdout"]["cases"],10)
            self.assertEqual(report["checkpoints"][-1]["episode"],55)
            self.assertNotEqual(report["pretraining_validation"]["source_manifest_sha256"],
                                report["independent_holdout"]["source_manifest_sha256"])
            for t in (trials[0],trials[-1]):
                raw=base64.b64decode(t["source_b64"])
                package=base64.b64decode(t["package_b64"])
                self.assertEqual(unpack(package),raw)
                self.assertEqual(digest(raw),t["metrics"]["source_sha256"])
            cold=PortfolioLedger(db)
            try:
                self.assertEqual(cold.verify()["rewarded_events"],55)
                self.assertEqual(cold.event(APP,"compression_000000")["reward"],
                                 trials[0]["metrics"]["reward"])
            finally:
                cold.close()
            with self.assertRaisesRegex(ValueError,"new independent"):
                run_learning(db,episodes=3,eval_cases=3)

    def test_holdout_evaluation_does_not_change_q_state(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=PortfolioLedger(Path(folder)/"fresh.sqlite")
            try:
                initial=ledger.verify()
                evaluation=evaluate(ledger,seed=909,count=8)
                self.assertEqual(ledger.verify(),initial)
                self.assertEqual(sum(evaluation["selection_counts"].values()),8)
                self.assertEqual(evaluation["budget_and_recall_success"]["standard"],1)
            finally:
                ledger.close()


if __name__=="__main__":
    unittest.main()
