"""Offline tests of honest Round 2 optimization scorekeeping.

Reference implementations are test controls, never passed to either author
model or the author jobs. This asserts that large stress correctness and
runtime instrumentation actually run instead of just returning a green flag.
"""
import json
from pathlib import Path
import tempfile
import unittest

from experiments.agent_arena import cases, author, optimize, opt_judge

LEDGER_OK = """from datetime import datetime
def parse(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))
def replay(events,as_of):
    limit=parse(as_of)
    chosen={}
    for event in events:
        if parse(event["at"])>limit: continue
        old=chosen.get(event["id"])
        if old is None or old["revision"]<event["revision"]:
            chosen[event["id"]]=event
    totals={}
    for event in chosen.values():
        key=event["account"]
        totals[key]=totals.get(key,0)+event["delta"]
    return totals
"""

GRAPH_OK = """def can_access(user,action,memberships,grants,denies):
    stack=[user]
    seen=set()
    any_allow=False
    while stack:
        node=stack.pop()
        if node in seen: continue
        seen.add(node)
        if action in denies.get(node, ()): return False
        if action in grants.get(node, ()): any_allow=True
        stack.extend(memberships.get(node, ()))
    return any_allow
"""


class Round2ProtocolTests(unittest.TestCase):
    def test_original_two_tasks_remain_stable_and_sealed(self):
        self.assertEqual(set(cases.CASES),{"ledger_revisions","permission_graph"})
        for case, spec in cases.CASES.items():
            self.assertEqual(len(cases.sealed_oracle_digest(case)),64)
            self.assertNotIn("test",cases.public_case(case))

    def test_separate_references_pass_old_oracle_and_large_stress(self):
        for case, source in [("ledger_revisions",LEDGER_OK),
                             ("permission_graph",GRAPH_OK)]:
            with self.subTest(case=case):
                self.assertEqual(opt_judge.judge.test_source(
                    source,cases.CASES[case]["test"])["status"],"passed")
                stress=opt_judge.stress_and_time(source,case)
                self.assertEqual(stress.get("stress_correct"),True,stress)
                self.assertGreater(stress.get("median_ns",0),0)
                self.assertEqual(len(stress.get("samples_ns",[])),9)

    def test_original_defects_fail_the_existing_oracle(self):
        for case, spec in cases.CASES.items():
            with self.subTest(case=case):
                verdict=opt_judge.judge.test_source(spec["source"],spec["test"])
                self.assertEqual(verdict["status"],"failed")

    def test_bad_optimized_source_is_never_credited(self):
        good=opt_judge.grade(LEDGER_OK,
                             cases.CASES["ledger_revisions"]["source"],
                             "ledger_revisions")
        self.assertFalse(good["eligible"])
        self.assertEqual(good["candidate_status"],"correctness_rejected")
        self.assertIsNone(good["speedup"])

    def test_equal_original_and_new_is_not_an_improvement(self):
        result=opt_judge.grade(GRAPH_OK,GRAPH_OK,"permission_graph")
        self.assertTrue(result["eligible"])
        self.assertGreater(result["speedup"],0)
        # This is repeated timing, not a claim that identical bytes improved.
        self.assertEqual(result["original_sha256"],result["candidate_sha256"])

    def test_stress_catches_policy_defect_even_if_module_is_valid(self):
        error=opt_judge.stress_and_time(
            cases.CASES["permission_graph"]["source"],"permission_graph")
        self.assertFalse(error["stress_correct"])

    def test_frozen_round1_requires_source_hash_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            original=cases.manifest()
            original["model_requested"]=author.MODEL
            original["agents_run"]=["bean","aider"]
            original["cases_run"]=list(cases.CASES)
            author.write_json(root/"author_manifest.json",original)
            for agent in ("bean","aider"):
                for case in cases.CASES:
                    folder=root/"authors"/agent/case
                    folder.mkdir(parents=True)
                    content=cases.CASES[case]["source"]
                    (folder/"candidate.py").write_text(content,encoding="utf-8")
                    author.write_json(folder/"receipt.json",{
                        "status":"candidate_drafted_not_tested",
                        "candidate_sha256":author.sha(content),
                        "task_source_sha256":author.sha(content)
                    })
            source,_=optimize.read_frozen_round1(root)
            self.assertEqual(len(source),4)
            target=root/"authors"/"aider"/"ledger_revisions"/"candidate.py"
            target.write_text("tampered",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"SHA mismatch"):
                optimize.read_frozen_round1(root)

    def test_optimization_goal_preserves_original_api(self):
        self.assertIn("preserving every externally observable",optimize.OPTIMIZE_GOAL)
        self.assertIn("runtime",optimize.OPTIMIZE_GOAL)
        self.assertEqual(optimize.ORIGINAL_RUN_ID,38110050070)


if __name__=="__main__":
    unittest.main()
