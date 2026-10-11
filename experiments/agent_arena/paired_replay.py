"""Independent paired, interleaved replay of BEAN vs Aider optimization artifacts.

The prior round benchmarked baseline and candidate in separate Python runs.
This replay measures *paired* original/optimized executions on identical inputs
within one credential-free interpreter, alternating execution order to reduce
drift. It does not change the published Round 2 verdict or prompt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

from experiments.agent_arena import author, cases, judge, opt_judge, optimize

ROUND2_RUN_ID = 38110686371
SAMPLE_PAIRS = 12
SIGNIFICANT_RATIO = 1.05
DIRECTIONAL_PAIRS = 9

# Compose the PREEXISTING held-out data/reference definitions with a new
# benchmarking main. This code is never included in author-model prompts.
COMMON_BENCH = opt_judge.BENCH_PROGRAM.split("\ndef main():", 1)[0].replace(
    "from candidate import replay, can_access",
    "import candidate_original\n"
    "import candidate_optimized\n"
    "replay = candidate_original.replay\n"
    "can_access = candidate_original.can_access"
)

PAIRED_MAIN = r'''
def main():
    case=sys.argv[1]
    if case=="ledger_revisions":
        jobs=run_ledger()
        before=candidate_original.replay
        after=candidate_optimized.replay
    elif case=="permission_graph":
        jobs=run_policy()
        before=candidate_original.can_access
        after=candidate_optimized.can_access
    else:
        raise ValueError("unknown case")
    for _, args in jobs:
        original_result=before(*args)
        updated_result=after(*args)
        assert original_result==updated_result, "candidate changed stress behavior"
    for _, args in jobs[:min(3,len(jobs))]:
        before(*args)
        after(*args)
    samples={"baseline":[],"optimized":[]}
    for index in range(12):
        # AB/BA sequence ensures neither version always runs first on a warm
        # or cold interpreter; both receive the *exact* same input objects.
        order=("baseline","optimized") if index%2==0 else (
            "optimized","baseline")
        for variant in order:
            gc.collect()
            fn=before if variant=="baseline" else after
            start=time.perf_counter_ns()
            for _,args in jobs:
                fn(*args)
            samples[variant].append(time.perf_counter_ns()-start)
    ratios=[a/b for a,b in zip(samples["baseline"],samples["optimized"])
            if a>0 and b>0]
    assert len(ratios)==12, "missing timing samples"
    result={
        "status":"correct_and_timed",
        "case":case,
        "jobs_per_pair":len(jobs),
        "paired_samples":len(ratios),
        "baseline_median_ns":int(statistics.median(samples["baseline"])),
        "optimized_median_ns":int(statistics.median(samples["optimized"])),
        "median_paired_speedup":round(statistics.median(ratios),5),
        "pairs_over_5pct":sum(value>1.05 for value in ratios),
        "pairs_under_minus_5pct":sum(value<0.95 for value in ratios),
        "paired_ratios":[round(value,5) for value in ratios],
    }
    print("BEAN_PAIRED_REPLAY:"+json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
'''


def sha(content):
    return hashlib.sha256(
        content.encode("utf-8") if isinstance(content, str) else content
    ).hexdigest()


def paired_timing(old, new, case, *, runner=subprocess.run):
    if case not in cases.CASES:
        raise ValueError("unknown preregistered case")
    with tempfile.TemporaryDirectory(prefix="bean-paired-opt-") as tmp:
        root = Path(tmp)
        for name, source in (("candidate_original", old),
                             ("candidate_optimized", new)):
            counterpart = (opt_judge.LEDGER_ADAPTER if case=="ledger_revisions"
                           else opt_judge.POLICY_ADAPTER)
            (root / (name + ".py")).write_text(source + counterpart,
                                                 encoding="utf-8")
        (root / "paired.py").write_text(COMMON_BENCH + "\n" + PAIRED_MAIN,
                                        encoding="utf-8")
        env = dict(os.environ)
        for name in ("OPENROUTER_API_KEY","GITHUB_TOKEN","GH_TOKEN",
                     "BEAN_MODELS_TOKEN"):
            env.pop(name, None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            process = runner(
                [sys.executable, "paired.py", case], cwd=root,
                env=env, capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {"status":"time_limit", "reason":"paired_benchmark_timeout"}
        if process.returncode != 0:
            return {"status":"failed", "reason":"paired_stress_or_runtime_error",
                    "stderr_sha256":sha(process.stderr[-2000:])}
        results=[line.split(":",1)[1] for line in process.stdout.splitlines()
                 if line.startswith("BEAN_PAIRED_REPLAY:")]
        if len(results)!=1:
            return {"status":"failed", "reason":"missing_paired_timing_receipt"}
        try:
            decoded=json.loads(results[0])
            if (decoded["paired_samples"]!=SAMPLE_PAIRS
                or decoded["jobs_per_pair"]<=0
                or decoded["baseline_median_ns"]<=0
                or decoded["optimized_median_ns"]<=0
                or len(decoded["paired_ratios"])!=SAMPLE_PAIRS):
                raise ValueError("invalid stats")
            return decoded
        except (KeyError, ValueError, TypeError):
            return {"status":"failed", "reason":"malformed_timing_receipt"}


def interpret(row):
    if row.get("status")!="correct_and_timed":
        return "INVALID"
    ratio=row["median_paired_speedup"]
    if ratio>SIGNIFICANT_RATIO and row["pairs_over_5pct"]>=DIRECTIONAL_PAIRS:
        return "FASTER_REPRODUCIBLE"
    if ratio<1/SIGNIFICANT_RATIO and row["pairs_under_minus_5pct"]>=DIRECTIONAL_PAIRS:
        return "SLOWER_REPRODUCIBLE"
    return "NO_CLEAR_CHANGE"


def evaluate(original_dir, optimized_dir):
    original,_=optimize.read_frozen_round1(original_dir)
    current=Path(optimized_dir)
    manifest=json.loads((current/"optimization_manifest.json").read_text())
    if (manifest.get("original_run_id")!=optimize.ORIGINAL_RUN_ID or
        manifest.get("model_requested")!=author.MODEL or
        manifest.get("case_public_sha256")!=cases.manifest()["case_public_sha256"] or
        manifest.get("oracle_sha256")!=cases.manifest()["oracle_sha256"] or
        manifest.get("initial_sha256")!={a:{c:sha(original[(a,c)])
                                       for c in cases.CASES} for a in ("bean","aider")}):
        raise ValueError("pinned original source and oracle contract mismatch")
    report={
        "schema":"bean.vs.aider.paired-replay.v1",
        "round1_run_id":optimize.ORIGINAL_RUN_ID,
        "round2_run_id":ROUND2_RUN_ID,
        "platform":sys.platform,
        "case_ids":list(cases.CASES),
        "outcomes":{},
        "scope":"replay_only_original_Round2_results_unchanged",
        "method":"12_interleaved_within_interpreter_original_candidate_pairs",
    }
    for agent in ("bean","aider"):
        report["outcomes"][agent]={}
        for case in cases.CASES:
            root=current/"authors"/agent/case
            receipt=json.loads((root/"receipt.json").read_text())
            if receipt.get("original_sha256")!=sha(original[(agent,case)]):
                raise ValueError("source baseline SHA mismatch")
            result={
                "author_status":receipt.get("status"), "candidate_sha256":None,
                "functional_baseline":judge.test_source(
                    original[(agent,case)],cases.CASES[case]["test"]),
                "paired_result":None, "paired_interpretation":"NOT_SUBMITTED",
            }
            if receipt.get("status")=="candidate_drafted_not_tested":
                file=root/"candidate.py"
                if not file.is_file() or file.is_symlink():
                    raise ValueError("candidate missing/invalid")
                code=file.read_text(encoding="utf-8")
                if sha(code)!=receipt.get("candidate_sha256"):
                    raise ValueError("candidate changed after original author run")
                result["candidate_sha256"]=sha(code)
                result["functional_candidate"]=judge.test_source(
                    code,cases.CASES[case]["test"])
                if result["functional_candidate"]["status"]=="passed" and result["functional_baseline"]["status"]=="passed":
                    result["paired_result"]=paired_timing(original[(agent,case)],
                                                           code,case)
                    result["paired_interpretation"]=interpret(result["paired_result"])
                else:
                    result["paired_interpretation"]="CORRECTNESS_REJECTED"
            report["outcomes"][agent][case]=result
    report["evidence_sha256"]=sha(json.dumps(report,sort_keys=True,separators=(",",":")))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--round1",type=Path,default=Path("_round1"))
    p.add_argument("--round2",type=Path,default=Path("_round2"))
    p.add_argument("--output",type=Path,default=Path("_paired/receipt.json"))
    args=p.parse_args()
    report=evaluate(args.round1,args.round2)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
