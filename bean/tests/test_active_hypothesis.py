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
