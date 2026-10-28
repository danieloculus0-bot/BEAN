"""No-solution-in-prompt tests for BEAN's local experiment planner."""
import tempfile
import unittest
from pathlib import Path
from bean.learning.active_hypothesis import act, discover, generate
from bean.learning.reasoning_service import NativeReasoningService
from bean.evaluation.active_abstraction_benchmark import World, benchmark


class ActiveHypothesisTests(unittest.TestCase):
    def test_composes_own_candidates_from_generic_grammar(self):
        candidates=generate(4)
        self.assertEqual(len(candidates),23)
        self.assertIn({"kind":"difference","lhs":0,"rhs":1,"polarity":-1},
                      candidates)
        self.assertIn({"kind":"constant","lhs":None,"rhs":None,"polarity":0},
                      candidates)
        self.assertEqual(act(candidates[0],(1,0,0,0)),-1)

    def test_rules_come_from_reward_and_observations_only(self):
        world=World(101,"difference")
        probes=[str(100+i) for i in range(40)]
        seen=[]
        def actual_reward(probe,action):
            seen.append((probe,action))
            return world.feedback(probe,action)
        outcome=discover(probe_ids=probes,observe=world.observe,
                         reward=actual_reward,budget=12)
        self.assertEqual(outcome["reward_calls"],36)
        self.assertEqual(outcome["sensor_observations"],40)
        self.assertEqual(outcome["observed_probe_ids"],probes)
        self.assertEqual(len(seen),36)
        self.assertTrue(set(case for case,_ in seen) <= set(probes))
        self.assertEqual({a for _,a in seen},{-1,0,1})
        self.assertEqual(outcome["status"],
                         "provisional_rule" if outcome["selected_rule"]
                         else "abstain")
        self.assertFalse(outcome["truth_oracle_used"])
        self.assertFalse(outcome["blind_cases_used"])

    def test_bad_evidence_fails_closed(self):
        world=World(202,"channel")
        ids=[str(100+i) for i in range(10)]
        with self.assertRaises(ValueError):
            discover(probe_ids=ids,observe=world.observe,
                     reward=lambda *_:float("nan"))
        with self.assertRaises(ValueError):
            discover(probe_ids=ids,observe=world.observe,
                     reward=world.feedback,budget=17)
        with self.assertRaises(ValueError):
            discover(probe_ids=ids,observe=lambda _: (1,),
                     reward=world.feedback)
        with self.assertRaises(ValueError):
            discover(probe_ids=ids[:2],observe=world.observe,
                     reward=world.feedback)

    def test_core_shares_ledger_and_recovers_rule(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"bean.sqlite3"
            world=World(120,"channel")
            core=NativeReasoningService(db)
            record=core.discover_analogy(
                domain="process control",task_ref="opaque-actuator",
                source_ref="host-sim:fixture-120",
                probe_ids=[str(100+i) for i in range(40)],
                observe=world.observe,reward=world.feedback,budget=12)
            self.assertTrue(record["evidence_retained"])
            self.assertFalse(record["external_model_invoked"])
            self.assertEqual(record["status"],"provisional_rule")
            earlier=core.use_discovered_analogy(
                receipt_id=record["receipt_id"], sensors=world.observe(9000))
            core.close()
            recovered=NativeReasoningService(db)
            try:
                later=recovered.use_discovered_analogy(
                    receipt_id=record["receipt_id"], sensors=world.observe(9000))
                self.assertEqual(earlier,later)
                with self.assertRaises(ValueError):
                    recovered.use_discovered_analogy(receipt_id="unknown",
                                                       sensors=(1,2,3,4))
                stored=[e for e in recovered.bank.journal.events()
                        if e["kind"]=="trial" and e["data"].get("experiment") ==
                        "bean.native.active_hypothesis.v1"]
                self.assertEqual(len(stored),1)
            finally:recovered.close()

    def test_persisted_rule_requires_exact_sensor_layout(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "layout.sqlite3"
            world = World(120, "channel")
            core = NativeReasoningService(db)
            original = core.discover_analogy(
                domain="controls", task_ref="sensor-schema",
                source_ref="fixture:four-channel",
                probe_ids=[str(100+i) for i in range(40)],
                observe=world.observe, reward=world.feedback, budget=12)
            self.assertEqual(original["status"], "provisional_rule")
            receipt = original["receipt_id"]
            valid = world.observe(9000)
            self.assertEqual(len(valid), 4)
            self.assertEqual(core.use_discovered_analogy(
                receipt_id=receipt, sensors=valid)["status"],
                "provisional_action")
            # Even when the learned rule uses only channel zero, extra or
            # missing channels change the meaning of the observation schema.
            for incompatible in (valid[:2], valid + (0.5,)):
                with self.subTest(dimensions=len(incompatible)):
                    with self.assertRaisesRegex(ValueError,
                                                "Incompatible sensor layout"):
                        core.use_discovered_analogy(
                            receipt_id=receipt, sensors=incompatible)
            core.close()
            recovered = NativeReasoningService(db)
            try:
                with self.assertRaisesRegex(ValueError,
                                            "Incompatible sensor layout"):
                    recovered.use_discovered_analogy(
                        receipt_id=receipt, sensors=valid[:2])
                self.assertEqual(recovered.use_discovered_analogy(
                    receipt_id=receipt, sensors=valid)["status"],
                    "provisional_action")
            finally:
                recovered.close()

    def test_new_feedback_can_revise_hypothesis(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"learning.sqlite3"
            world=World(120,"channel")
            core=NativeReasoningService(db)
            original=core.discover_analogy(
                domain="controls",task_ref="original-world",
                source_ref="fixture:control-before",
                probe_ids=[str(100+i) for i in range(40)],
                observe=world.observe,reward=world.feedback,budget=12)
            self.assertEqual(original["status"],"provisional_rule")
            changed_feedback=lambda case,action: world.feedback(case,-action)
            revision=core.revise_discovered_analogy(
                parent_receipt_id=original["receipt_id"],
                domain="controls",task_ref="changed-world",
                source_ref="fixture:control-after",
                probe_ids=[str(200+i) for i in range(40)],
                observe=world.observe,reward=changed_feedback,budget=12)
            self.assertEqual(revision["status"],"provisional_rule")
            self.assertEqual(revision["revision_decision"],
                             "updated_from_fresh_feedback")
            self.assertEqual(revision["ancestry_observation_coverage"],
                             "all_observed_probe_ids")
            self.assertGreater(revision["fresh_advantage_per_probe"],0.08)
            self.assertNotEqual(revision["selected_rule"],
                                original["selected_rule"])
            unseen=[str(600+i) for i in range(30)]
            old_correct=sum(world.feedback(case,-act(
                original["selected_rule"],world.observe(case))) for case in unseen)
            new_correct=sum(world.feedback(case,-act(
                revision["selected_rule"],world.observe(case))) for case in unseen)
            self.assertGreater(new_correct,old_correct)
            with self.assertRaisesRegex(ValueError,"unseen probe"):
                core.revise_discovered_analogy(
                    parent_receipt_id=revision["receipt_id"],
                    domain="controls",task_ref="duplicate",
                    source_ref="fixture:duplicate",
                    probe_ids=[revision["records"][0]["probe_id"]]+
                              [str(700+i) for i in range(39)],
                    observe=world.observe,reward=changed_feedback,budget=12)
            # The original experiment observed 40 sensors but rewarded only
            # 12. An unrewarded sensor is still previously seen evidence.
            rewarded={row["probe_id"] for row in original["records"]}
            observed_only=next(pid for pid in original["observed_probe_ids"]
                               if pid not in rewarded)
            with self.assertRaisesRegex(ValueError,"unseen probe"):
                core.revise_discovered_analogy(
                    parent_receipt_id=revision["receipt_id"],
                    domain="controls",task_ref="observed-but-unrewarded",
                    source_ref="fixture:unrewarded-reuse",
                    probe_ids=[observed_only]+[str(800+i) for i in range(39)],
                    observe=world.observe,reward=changed_feedback,budget=12)
            self.assertEqual(len([e for e in core.bank.journal.events()
                if e["kind"]=="trial" and e["data"].get("experiment") ==
                "bean.native.active_hypothesis.v1"]),2)
            old_action=core.use_discovered_analogy(
                receipt_id=original["receipt_id"],sensors=world.observe(9000))
            new_action=core.use_discovered_analogy(
                receipt_id=revision["receipt_id"],sensors=world.observe(9000))
            self.assertEqual(old_action["action"],-new_action["action"])
            core.close()
            recovered=NativeReasoningService(db)
            try:
                self.assertEqual(recovered.use_discovered_analogy(
                    receipt_id=revision["receipt_id"],
                    sensors=world.observe(9000)),new_action)
                self.assertEqual(recovered.use_discovered_analogy(
                    receipt_id=original["receipt_id"],
                    sensors=world.observe(9000)),old_action)
            finally:
                recovered.close()

    def test_revision_rejects_bad_parent_and_invalid_gain(self):
        with tempfile.TemporaryDirectory() as d:
            core=NativeReasoningService(Path(d)/"reason.sqlite")
            world=World(120,"channel")
            params=dict(parent_receipt_id="not-a-real-receipt",
                        domain="controls",task_ref="bad",source_ref="fixture:bad",
                        probe_ids=[str(500+i) for i in range(40)],
                        observe=world.observe,reward=world.feedback)
            with self.assertRaisesRegex(ValueError,"Unknown previous"):
                core.revise_discovered_analogy(**params)
            with self.assertRaisesRegex(ValueError,"min_gain"):
                core.revise_discovered_analogy(**params,min_gain=float("nan"))
            core.close()

    def test_blind_suite_is_repeatable_and_discloses_misses(self):
        r=benchmark(worlds_per_family=3,budgets=(3,6))
        again=benchmark(worlds_per_family=3,budgets=(3,6))
        self.assertEqual(r["summary"],again["summary"])
        self.assertEqual(len(r["individual_world_results"]),24)
        self.assertFalse(any(row["blind_cases"]!=60
                             for row in r["individual_world_results"]))
        self.assertTrue(r["hypothesis_grammar_is_handwritten"])
        self.assertFalse(r["model_independently_builds_grammar"])


if __name__=="__main__":
    unittest.main()
