"""End-to-end durable state memory contract, no model or external network."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bean.optimization.portfolio_ledger import PortfolioLedger, canonical


class PortfolioLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "bean-state.db"
        self.ledger = PortfolioLedger(self.path)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def add(self, event="e1", **kwargs):
        args = dict(app="FUN/EmperorGauntlet", event_id=event,
                    state="wave3/night/near", action="flee", reward=1.0,
                    next_state="wave3/night/far", done=False,
                    evidence_ref="sim://episode-1", revision="test-sha",
                    kind="synthetic", tags=("game", "night"))
        args.update(kwargs)
        return self.ledger.observe(**args)

    def test_learning_restore_receipt_duplicate_and_replay(self):
        first = self.add()
        self.assertTrue(first["new"])
        self.assertEqual(first["receipt"], self.add()["receipt"])
        self.assertEqual(self.ledger.verify()["events"], 1)
        self.assertAlmostEqual(self.ledger._q("FUN/EmperorGauntlet",
                               "wave3/night/near")["flee"], .23)
        self.ledger.close()
        self.ledger = PortfolioLedger(self.path)
        self.add("e2", reward=-1.0, done=True)
        verified = self.ledger.verify()
        self.assertEqual(verified["events"],2)
        self.assertEqual(verified["q_entries"],1)
        self.assertLess(self.ledger._q("FUN/EmperorGauntlet",
                        "wave3/night/near")["flee"],.23)
        self.assertEqual(self.ledger.event("FUN/EmperorGauntlet","e1")["reward"],1.0)

    def test_conflicting_identity_rolls_back_and_no_double_credit(self):
        self.add()
        with self.assertRaisesRegex(ValueError,"conflicting"):
            self.add(reward=77)
        self.assertEqual(self.ledger.verify()["events"],1)

    def test_apps_do_not_share_policy_or_evidence(self):
        self.add()
        self.add("e1", app="Axiom_Beta",state="inspection/review",
                 action="review",reward=0.5)
        self.assertEqual(self.ledger.verify()["events"],2)
        self.assertEqual(self.ledger._q("Axiom_Beta","wave3/night/near"),{})
        self.assertEqual(self.ledger.event("Axiom_Beta","e1")["app"],"Axiom_Beta")
        self.assertIsNone(self.ledger.event("AIscend","e1"))

    def test_unverified_observation_does_not_learn(self):
        self.add("note",reward=None,action=None,kind="unverified")
        self.assertEqual(self.ledger.verify()["q_entries"],0)

    def test_bounded_recall_and_exact_recovery(self):
        for i in range(30):
            self.add(f"night-{i}",state="wave3/night/near" if i%2 else "wave1/day/far",
                     reward=(-1)**i)
        context = self.ledger.state_context(
            app="FUN/EmperorGauntlet", query="night", max_bytes=750)
        self.assertLessEqual(len(canonical(context)),750)
        self.assertEqual(context["total_events"],30)
        self.assertTrue(context["truncated"])
        self.assertEqual(self.ledger.verify()["events"],30)
        self.assertEqual(self.ledger.event("FUN/EmperorGauntlet","night-29")["reward"],-1)

    def test_unverified_event_cannot_train_a_policy(self):
        with self.assertRaisesRegex(ValueError,"unverified"):
            self.add("bogus",kind="unverified",reward=100)
        self.assertEqual(self.ledger.verify()["events"],0)

    def test_portfolio_context_sees_multiple_apps_without_policy_mixing(self):
        self.add()
        self.add("another",app="Axiom_Beta",state="planning/late",
                 action="review",reward=-0.5)
        result=self.ledger.portfolio_context(max_bytes=700)
        self.assertEqual(result["apps_total"],2)
        self.assertEqual({r["app"] for r in result["apps"]},
                         {"Axiom_Beta","FUN/EmperorGauntlet"})
        self.assertLessEqual(len(canonical(result)),700)
        self.assertEqual(self.ledger.verify()["events"],2)

    def test_compact_reward_scoreboard_rebuilds_with_negative_results(self):
        self.add("positive",reward=2)
        self.add("negative",reward=-1)
        self.add("no-credit",reward=None,action=None,kind="unverified")
        scoreboard=self.ledger.state_context(app="FUN/EmperorGauntlet",
                                             max_bytes=1500)["rewards"]
        self.assertEqual(scoreboard["positive"],1)
        self.assertEqual(scoreboard["negative"],1)
        self.assertEqual(scoreboard["rewarded"],2)
        self.assertEqual(scoreboard["reward_sum"],1)
        self.assertEqual(self.ledger.verify()["rewarded_events"],2)
        self.ledger.db.execute(
            "UPDATE portfolio_scores SET positive=99 WHERE app=?",
            ("FUN/EmperorGauntlet",))
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError,"scoreboard diverges"):
            self.ledger.verify()

    def test_tamper_detection(self):
        self.add()
        self.ledger.db.execute(
            "UPDATE portfolio_events SET chain_hash=? WHERE seq=1",("0"*64,))
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError,"corrupted"):
            self.ledger.verify()

    def test_divergent_q_state_detection(self):
        self.add()
        self.ledger.db.execute("UPDATE portfolio_q SET value=999")
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError,"diverges"):
            self.ledger.verify()

    def test_no_reward_without_evidence_and_rollback(self):
        with self.assertRaises(ValueError):
            self.add(evidence_ref="")
        with self.assertRaises(ValueError):
            self.add(reward=float("nan"))
        self.assertEqual(self.ledger.verify()["events"],0)


if __name__ == "__main__":
    unittest.main()
