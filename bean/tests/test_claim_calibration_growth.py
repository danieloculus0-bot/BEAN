"""Claim-truth growth must retain wrong claims and never invent success."""
from __future__ import annotations

from dataclasses import replace
import gzip
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from bean.evaluation.claim_calibration_growth import (
    ACTIONS,APP,AdjudicatedOutcome,accept_feedback,decide,digest,
    evaluate,experiment,make_case,message,reward_for,run_all,state_for)
from bean.optimization.portfolio_ledger import PortfolioLedger


class ClaimTruthGrowthTests(unittest.TestCase):
    def test_false_positive_cost_and_uncertainty(self):
        self.assertEqual(reward_for("tentative",False),-4.0)
        self.assertEqual(reward_for("tentative",True),2.0)
        self.assertGreater(reward_for("unknown",False),0)
        self.assertLess(reward_for("unknown",True),0)
        self.assertEqual(set(ACTIONS),{"tentative","qualify","unknown"})
        for action in ACTIONS:
            claim,_=make_case(11,2,phase="train")
            text=message(claim,action)
            self.assertNotIn("confirmed success",text.lower())
            self.assertNotIn("independently verified",text.lower())

    def test_preposterous_confidence_is_not_ground_truth(self):
        claim,oracle=make_case(11,4,phase="train")
        claim=replace(claim,declared_verified=True,source_confidence=.99,
                      source="boastful_agent")
        with tempfile.TemporaryDirectory() as path:
            ledger=PortfolioLedger(Path(path)/"learning.sqlite")
            try:
                self.assertIn("boastful_agent",state_for(claim))
                with self.assertRaisesRegex(ValueError,"oracle"):
                    accept_feedback(ledger,claim,"tentative",None)
                with self.assertRaisesRegex(ValueError,"oracle"):
                    accept_feedback(ledger,claim,"tentative",
                                    AdjudicatedOutcome(claim.case_id,False,"0"*64))
                self.assertEqual(ledger.verify()["rewarded_events"],0)
                self.assertEqual(ledger._q(APP,state_for(claim)),{})
                # Claimed verification and high confidence are merely FEATURES.
                # Only the synthetic withheld oracle can supply a scored label.
                signed=AdjudicatedOutcome(
                    claim.case_id,False,
                    digest({"case_id":claim.case_id,"supported":False,
                            "source":"synthetic_hidden_oracle_v1"}))
                res=accept_feedback(ledger,claim,"tentative",signed)
                self.assertEqual(res["reward"],-4)
                self.assertEqual(ledger.verify()["rewarded_events"],1)
                repeat=accept_feedback(ledger,claim,"tentative",signed)
                self.assertFalse(repeat["new"])
                self.assertEqual(ledger.verify()["rewarded_events"],1)
            finally:
                ledger.close()

    def test_retains_corrections_and_holdout_does_not_train(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"experiment"
            report=experiment(out,11,episodes=90,holdout=38)
            self.assertEqual(report["actual_BEAN_Q_updates"],90)
            self.assertEqual(report["Q_verification"]["events"],90)
            self.assertEqual(report["archive"]["rows"],128)
            self.assertTrue(report["archive"]["reversible"])
            self.assertEqual(report["claims_promoted_to_verified"],0)
            self.assertEqual(report["holdout"]["count"],38)
            self.assertEqual(report["holdout_domains"],
                             ["robotics","maintenance","inventory"])
            data=json.loads(gzip.decompress(
                (out/"original_trial_evidence.json.gz").read_bytes()))
            self.assertEqual(len(data["training"]),90)
            self.assertEqual(len(data["holdout"]),38)
            self.assertNotIn("oracle",data["training"][0]["claim"])
            ledger=PortfolioLedger(out/"claim_q.sqlite")
            try:
                self.assertEqual(ledger.verify()["rewarded_events"],90)
                original=ledger.event(APP,"train_11_000000")
                self.assertEqual(original["reward"],data["training"][0]["outcome"]["reward"])
                before=ledger.verify()
                _=evaluate(ledger,seed=100012,count=30)
                self.assertEqual(ledger.verify(),before)
            finally:
                ledger.close()
            with self.assertRaisesRegex(ValueError,"new isolated"):
                experiment(out,11,episodes=2,holdout=20)

    def test_reproducible_unseen_seeds_and_credible_scoreboard(self):
        with tempfile.TemporaryDirectory() as td:
            report=run_all(Path(td),seeds=(11,23),episodes=80,holdout=24)
            self.assertEqual(report["real_bean_Q_updates"],160)
            self.assertEqual(report["sealed_holdout_cases"],48)
            self.assertEqual(report["language_model_calls"],0)
            self.assertFalse(report["independent_real_world_success_proven"])
            self.assertNotEqual(report["per_seed"][0]["source_hash"],
                                report["per_seed"][1]["source_hash"])
            self.assertEqual(set(report["mean_heldout_utility"]),
                {"BEAN_Q","boast_accepting","always_qualify","always_unknown"})

    def test_cold_q_integrity_flags_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"experiment"
            experiment(out,29,episodes=21,holdout=20)
            db=out/"claim_q.sqlite"
            conn=sqlite3.connect(db)
            conn.execute("UPDATE portfolio_q SET value=999 WHERE app=?",(APP,))
            conn.commit()
            conn.close()
            ledger=PortfolioLedger(db)
            try:
                with self.assertRaisesRegex(ValueError,"diverges"):
                    ledger.verify()
            finally:
                ledger.close()

    def test_self_supplied_verification_is_not_a_proof(self):
        claim,_=make_case(11,2,phase="train")
        pretend=replace(claim,declared_verified=True,source_confidence=.99)
        self.assertNotIn("verified",message(pretend,"tentative").split(";")[0].lower())
        self.assertEqual(make_case(11,2,phase="train")[0],
                         make_case(11,2,phase="train")[0])
        self.assertNotEqual(make_case(11,2,phase="train")[0].domain,
                            make_case(11,2,phase="holdout")[0].domain)


if __name__=="__main__":
    unittest.main()
