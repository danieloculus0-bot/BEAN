"""Independent tests for paired optimization timing replay.

No model call is made, and timing differences are only evidence when the
same-interpreter pairs consistently show material gains.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace

from experiments.agent_arena import paired_replay as paired


LEDGER = """from datetime import datetime
def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
def replay(events,as_of):
    cutoff=parse(as_of)
    best={}
    for row in events:
        if parse(row["at"])>cutoff: continue
        old=best.get(row["id"])
        if old is None or row["revision"]>old["revision"]:
            best[row["id"]]=row
    totals={}
    for row in best.values():
        totals[row["account"]]=totals.get(row["account"],0)+row["delta"]
    return totals
"""

GRAPH = """def can_access(user,action,memberships,grants,denies):
    pending=[user]
    visited=set()
    permitted=False
    while pending:
        group=pending.pop()
        if group in visited: continue
        visited.add(group)
        if action in denies.get(group,()): return False
        if action in grants.get(group,()): permitted=True
        pending.extend(memberships.get(group,()))
    return permitted
"""


class PairedReplayTests(unittest.TestCase):
    def test_both_known_correct_reference_modules_pass_paired_stress(self):
        for case, source in (("ledger_revisions",LEDGER),
                             ("permission_graph",GRAPH)):
            with self.subTest(case=case):
                result=paired.paired_timing(source,source,case)
                self.assertEqual(result["status"],"correct_and_timed",result)
                self.assertEqual(result["paired_samples"],12)
                self.assertEqual(len(result["paired_ratios"]),12)
                self.assertGreater(result["baseline_median_ns"],0)
                self.assertGreater(result["optimized_median_ns"],0)

    def test_broken_code_cannot_generate_benchmark_speedup(self):
        result=paired.paired_timing(GRAPH,"def can_access(*x): return True\n",
                                   "permission_graph")
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["reason"],"paired_stress_or_runtime_error")

    def test_directional_threshold_needs_nine_consistent_pairs(self):
        template={"status":"correct_and_timed","median_paired_speedup":1.12,
                  "pairs_over_5pct":10,"pairs_under_minus_5pct":0}
        self.assertEqual(paired.interpret(template),"FASTER_REPRODUCIBLE")
        template["pairs_over_5pct"]=8
        self.assertEqual(paired.interpret(template),"NO_CLEAR_CHANGE")
        template.update(median_paired_speedup=0.8,
                        pairs_over_5pct=0,pairs_under_minus_5pct=10)
        self.assertEqual(paired.interpret(template),"SLOWER_REPRODUCIBLE")
        template["status"]="failed"
        self.assertEqual(paired.interpret(template),"INVALID")

    def test_timing_subprocess_has_no_inference_or_github_tokens(self):
        envseen={}
        fake_receipt={
            "status":"correct_and_timed",
            "case":"permission_graph","jobs_per_pair":2,
            "paired_samples":12,"baseline_median_ns":100,
            "optimized_median_ns":90,"median_paired_speedup":1.111,
            "paired_ratios":[1.111]*12,"pairs_over_5pct":12,
            "pairs_under_minus_5pct":0,
        }
        def fake(*args,**kwargs):
            envseen.update(kwargs["env"])
            return SimpleNamespace(returncode=0,stderr="",
                 stdout="BEAN_PAIRED_REPLAY:"+json.dumps(fake_receipt)+"\n")
        from unittest.mock import patch
        with patch.dict(paired.os.environ,{
             "OPENROUTER_API_KEY":"fictional",
             "GITHUB_TOKEN":"fictional",
             "GH_TOKEN":"fictional",
             "BEAN_MODELS_TOKEN":"fictional"}):
            result=paired.paired_timing(GRAPH,GRAPH,"permission_graph",
                                        runner=fake)
        self.assertEqual(result["paired_samples"],12)
        for name in ("OPENROUTER_API_KEY","GITHUB_TOKEN",
                     "GH_TOKEN","BEAN_MODELS_TOKEN"):
            self.assertNotIn(name,envseen)

    def test_timing_receipt_cannot_declare_success_without_samples(self):
        def fabricated(*args,**kwargs):
            return SimpleNamespace(returncode=0,stderr="",stdout=
                       'BEAN_PAIRED_REPLAY:{"status":"correct_and_timed",'
                       '"paired_samples":12,"jobs_per_pair":1}\n')
        result=paired.paired_timing(GRAPH,GRAPH,"permission_graph",
                                    runner=fabricated)
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["reason"],"malformed_timing_receipt")

    def test_original_and_optimized_source_are_distinctly_imported(self):
        self.assertIn("candidate_original",paired.COMMON_BENCH)
        self.assertIn("candidate_optimized",paired.COMMON_BENCH)
        self.assertIn("baseline",paired.PAIRED_MAIN)
        self.assertIn("optimized",paired.PAIRED_MAIN)
        self.assertIn("gc.collect()",paired.PAIRED_MAIN)


if __name__=="__main__":
    unittest.main()
