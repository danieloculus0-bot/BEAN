"""Independent stress correctness + optimization timing for Round 2.

This module is used only by secret-free GitHub CI. Agents receive task
description and their own frozen previous code, not its stress cases.
Whole source executions occur in isolated temporary runner subprocesses.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
from experiments.agent_arena import cases, author, judge, optimize

BENCH_PROGRAM = r'''
import datetime
import gc
import json
import random
import statistics
import sys
import time
from candidate import replay, can_access

def ledger_reference(events, as_of):
    def stamp(v):
        return datetime.datetime.fromisoformat(v.replace("Z","+00:00"))
    limit=stamp(as_of)
    best={}
    for row in events:
        if stamp(row["at"]) > limit:
            continue
        id=row["id"]
        if id not in best or row["revision"] > best[id]["revision"]:
            best[id]=row
    totals={}
    for row in best.values():
        totals[row["account"]]=totals.get(row["account"],0)+row["delta"]
    return totals

def policy_reference(user, action, memberships, grants, denies):
    pending=[user]
    seen=set()
    allow=False
    while pending:
        node=pending.pop()
        if node in seen: continue
        seen.add(node)
        if action in denies.get(node, ()): return False
        if action in grants.get(node, ()): allow=True
        pending.extend(memberships.get(node, ()))
    return allow

def run_ledger():
    rng=random.Random(719713)
    datasets=[]
    cutoff="2026-10-09T19:30:00-05:00"
    for batch in range(3):
        rows=[]
        for i in range(7500):
            key=str(batch)+"-"+str(i)
            account="acct"+str(i%53)
            at="2026-10-10T00:10:00+00:00"
            rows.extend([
                {"id":key, "revision":1, "account":account,
                 "delta":(i%7)-2, "at":at},
                {"id":key, "revision":2, "account":account,
                 "delta":(i%17)-6, "at":at},
                {"id":key, "revision":3, "account":account,
                 "delta":(i%29)-11,
                 "at":("2026-10-10T00:31:00Z" if i%5==0 else at)},
            ])
            if i%9==0:
                rows.append(dict(rows[-1]))
        rng.shuffle(rows)
        datasets.append((rows,cutoff))
    for rows,at in datasets:
        assert replay(rows,at)==ledger_reference(rows,at), "stress ledger mismatch"
        assert replay(list(reversed(rows)),at)==ledger_reference(rows,at), "order dependence"
        assert replay(rows,"2026-10-10T00:30:00Z")==replay(rows,at), "instant dependence"
    return [(replay,(rows,at)) for rows,at in datasets]

def run_policy():
    links={}
    for i in range(1200):
        links["g"+str(i)] = ([] if i==1199 else ["g"+str(i+1)])
    links["g1199"]=["g410"]
    links["u"]=["g0","g17"]
    grants={"g1199":["read"],"g31":["write"]}
    denies={"g1198":["write"]}
    tests=[]
    for j in range(40):
        user="u" if j%3 else "g"+str(j*17)
        action=("read" if j%2 else "write")
        tests.append((user,action,links,grants,denies))
    rng=random.Random(994)
    for j in range(24):
        branches=rng.sample(range(1200),3)
        links["fork"+str(j)]=["g"+str(i) for i in branches]
        tests.append(("fork"+str(j),"read",links,grants,denies))
    for item in tests:
        assert can_access(*item)==policy_reference(*item), "stress graph mismatch"
    # No mutation from traversal; repeated inputs must remain equivalent.
    assert links["u"]==["g0","g17"], "mutated membership input"
    return [(can_access,item) for item in tests]

def main():
    case=sys.argv[1]
    if case=="ledger_revisions":
        jobs=run_ledger()
    elif case=="permission_graph":
        jobs=run_policy()
    else: raise ValueError("unsupported task")
    for fn,args in jobs[:min(3,len(jobs))]: fn(*args)
    # Alternating all 3 ledger inputs and varied graph queries discourages
    # overfitting a single repeated argument with memoization.
    durations=[]
    for repeat in range(9):
        gc.collect()
        start=time.perf_counter_ns()
        if case=="ledger_revisions":
            for fn,args in jobs: fn(*args)
        else:
            for fn,args in jobs: fn(*args)
        durations.append(time.perf_counter_ns()-start)
    print("BEAN_ARENA_BENCH_RESULT:"+json.dumps({
        "case":case,"median_ns":int(statistics.median(durations)),
        "samples_ns":durations,"jobs_per_sample":len(jobs),
        "stress_correct":True,
    },sort_keys=True))

if __name__=="__main__":
    main()
'''
# The snippet imports both named public functions. Each candidate has only
# ONE task module, so append its companion name only for import compatibility.
LEDGER_ADAPTER = "\ndef can_access(*args):\n    raise NotImplementedError\n"
POLICY_ADAPTER = "\ndef replay(*args):\n    raise NotImplementedError\n"


def sha(data):
    return hashlib.sha256(
        data.encode("utf-8") if isinstance(data, str) else data
    ).hexdigest()


def stress_and_time(code, case):
    with tempfile.TemporaryDirectory(prefix="bean-round2-judge-") as tmp:
        root = Path(tmp)
        adapter = LEDGER_ADAPTER if case == "ledger_revisions" else POLICY_ADAPTER
        (root / "candidate.py").write_text(code+adapter, encoding="utf-8")
        (root / "bench.py").write_text(BENCH_PROGRAM, encoding="utf-8")
        env = dict(__import__("os").environ)
        for k in ("OPENROUTER_API_KEY","GITHUB_TOKEN","GH_TOKEN","BEAN_MODELS_TOKEN"):
            env.pop(k,None)
        env["PYTHONDONTWRITEBYTECODE"]="1"
        try:
            p = subprocess.run([sys.executable,"bench.py",case],cwd=root,
                               env=env,capture_output=True,text=True,timeout=90)
            if p.returncode != 0:
                return {"stress_correct":False,"reason":"stress_error",
                        "stderr_sha256":sha(p.stderr[-3000:])}
            lines=[s for s in p.stdout.splitlines()
                   if s.startswith("BEAN_ARENA_BENCH_RESULT:")]
            if len(lines)!=1:
                return {"stress_correct":False,"reason":"missing_benchmark_receipt"}
            value=json.loads(lines[0].split(":",1)[1])
            if not value.get("stress_correct") or value.get("median_ns",0)<=0:
                return {"stress_correct":False,"reason":"invalid_benchmark_receipt"}
            return value
        except subprocess.TimeoutExpired:
            return {"stress_correct":False,"reason":"stress_timeout"}


def grade(old, new, case):
    spec=cases.CASES[case]
    results={
        "original_sha256":sha(old),
        "baseline_tests":judge.test_source(old,spec["test"]),
        "baseline_stress":stress_and_time(old,case),
    }
    if new is None:
        results.update(candidate_status="not_submitted",
                       optimized_tests=None,optimized_stress=None,
                       speedup=None,eligible=False)
        return results
    results["candidate_sha256"]=sha(new)
    results["optimized_tests"]=judge.test_source(new,spec["test"])
    results["optimized_stress"]=stress_and_time(new,case)
    base=results["baseline_stress"]
    opt=results["optimized_stress"]
    eligible = (
        results["baseline_tests"]["status"]=="passed" and
        results["optimized_tests"]["status"]=="passed" and
        base.get("stress_correct") is True and
        opt.get("stress_correct") is True
    )
    results["eligible"]=eligible
    results["candidate_status"]="valid" if eligible else "correctness_rejected"
    if eligible:
        results["speedup"]=round(base["median_ns"]/opt["median_ns"],4)
        results["saved_percent"]=round(
            100*(1-opt["median_ns"]/base["median_ns"]),2)
    else:
        results["speedup"]=None
        results["saved_percent"]=None
    return results


def evaluate(previous_root,current_root):
    # Independently re-check the immutability contract of Round 1's artifacts.
    original,_=optimize.read_frozen_round1(previous_root)
    manifest=json.loads((Path(current_root)/"optimization_manifest.json").read_text())
    expected=cases.manifest()
    for field in ("case_public_sha256","oracle_sha256","case_ids"):
        if manifest.get(field)!=expected.get(field):
            raise ValueError("Round 2 manifest mismatches sealed original task suite")
    if manifest.get("original_run_id")!=optimize.ORIGINAL_RUN_ID:
        raise ValueError("Round 2 baseline run changed")
    if manifest.get("model_requested")!=author.MODEL:
        raise ValueError("Competitors did not request the same declared model")
    if manifest.get("initial_sha256") != {
        agent:{name:sha(original[(agent,name)]) for name in cases.CASES}
        for agent in ("bean","aider")
    }:
        raise ValueError("Frozen original code does not match the optimization targets")
    report={"schema":"bean.vs.aider.optimization.verdict.v1",
            "round1_run_id":optimize.ORIGINAL_RUN_ID,
            "model_requested":author.MODEL,
            "cases":{},"aggregates":{},"winner":"INCONCLUSIVE",
            "honest_limitations":[
                "Execution time is measured on one runner and is subject to noise.",
                "Aider internals may use different model-call counts from BEAN.",
                "Only two synthetic tasks; not a proof of general coding-agent superiority.",
            ]}
    for agent in ("bean","aider"):
        report["cases"][agent]={}
        for case in cases.CASES:
            folder=Path(current_root)/"authors"/agent/case
            receipt=json.loads((folder/"receipt.json").read_text())
            if receipt.get("original_sha256")!=sha(original[(agent,case)]):
                raise ValueError("Task baseline hash changed")
            candidate=None
            target=folder/"candidate.py"
            if receipt.get("status")=="candidate_drafted_not_tested":
                if not target.is_file() or target.is_symlink():
                    raise ValueError("Missing or invalid candidate file")
                candidate=target.read_text(encoding="utf-8")
                if sha(candidate)!=receipt.get("candidate_sha256"):
                    raise ValueError("Candidate digest changed after authoring")
            elif target.exists():
                raise ValueError("Unexpected model source without candidate receipt")
            verdict=grade(original[(agent,case)],candidate,case)
            verdict["author_status"]=receipt["status"]
            verdict["model_requested"]=receipt.get("model_requested")
            verdict["wall_seconds"]=receipt.get("wall_seconds")
            verdict["attempts"]=receipt.get("attempts")
            report["cases"][agent][case]=verdict
    valid_all={}
    for agent in ("bean","aider"):
        by_case=report["cases"][agent]
        valid_all[agent]=all(row["eligible"] for row in by_case.values())
        report["aggregates"][agent]={
            "valid_optimized_tasks":sum(row["eligible"] for row in by_case.values()),
            "original_all_correct":all(row["baseline_tests"]["status"]=="passed"
                                      and row["baseline_stress"].get("stress_correct")
                                      for row in by_case.values()),
            "mean_relative_speedup":round(sum((row["speedup"] or 0)
                                              for row in by_case.values())/len(by_case),4)
                                       if valid_all[agent] else None,
        }
    if valid_all["bean"] and valid_all["aider"]:
        be=report["aggregates"]["bean"]["mean_relative_speedup"]
        ai=report["aggregates"]["aider"]["mean_relative_speedup"]
        # +/-5% in mean gain is a tie to avoid claiming noisy performance wins.
        report["winner"]="BEAN_OPTIMIZATION_ADVANTAGE" if be>ai*1.05 else (
            "AIDER_OPTIMIZATION_ADVANTAGE" if ai>be*1.05 else "STATISTICAL_TIE")
    else:
        report["winner"]="INCONCLUSIVE_OR_INCOMPLETE"
    report["evidence_sha256"]=sha(json.dumps(report,sort_keys=True,separators=(",",":")))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--round1",type=Path,default=Path("_round1"))
    p.add_argument("--round2",type=Path,default=Path("_round2"))
    p.add_argument("--out",type=Path,default=Path("_opt_verdict/report.json"))
    args=p.parse_args()
    result=evaluate(args.round1,args.round2)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8")
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
