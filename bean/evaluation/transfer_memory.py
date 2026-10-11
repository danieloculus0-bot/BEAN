"""BEAN Lab021b: evidence-selected unsolved task and independent final score.

Only source-verified, already completed assessment artifacts authorize skipping
a task. The free-model job sees counts but not oracle examples, source code,
past hidden test inputs, or evaluator stack traces.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

IDS = ("intervals", "dependencies", "inventory")


def read(path: Path, phase: str) -> dict:
    x = json.loads(path.read_text(encoding="utf-8"))
    if (x.get("schema") != "bean.autonomy.lab021.evaluation.v1" or
            x.get("phase") != phase or
            set(t["task_id"] for t in x["tasks"]) != set(IDS)):
        raise ValueError("unsupported or incomplete evidence report")
    return {t["task_id"]: t for t in x["tasks"]}


def prepare(report_a: Path, report_b: Path, output: Path) -> dict:
    a, b = read(report_a, "holdout"), read(report_b, "holdout")
    # These explicit source run IDs point to immutable GitHub Actions artifacts.
    sources = {"intervals": (a["intervals"], 38108649668),
               "dependencies": (b["dependencies"], 38108708826)}
    for name, (evidence, run_id) in sources.items():
        if (evidence["status"] != "evaluated" or evidence["passed"] != evidence["total"]
                or evidence["total"] < 50):
            raise ValueError(f"unverified solved task: {name}")
    feedback = {
        "schema": "bean.autonomy.lab021b.selection.v1",
        "evidence_runs": [38108649668, 38108708826],
        "rule": "Retain two independently passing source modules; investigate only unresolved inventory",
        "tasks": [
            {"task_id": name,
             "passed": sources[name][0]["passed"] if name in sources else 0,
             "total": sources[name][0]["total"] if name in sources else a[name]["total"],
             "evidence_run_id": sources[name][1] if name in sources else None}
            for name in IDS
        ],
    }
    if [x["task_id"] for x in feedback["tasks"] if x["passed"] < x["total"]] != ["inventory"]:
        raise ValueError("unexpected investigation priority")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(feedback, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return feedback


def compile_results(report_a: Path, report_b: Path, report_c: Path, output: Path) -> dict:
    a, b, c = (read(path, "final") for path in (report_a, report_b, report_c))
    chosen = {"intervals": (a["intervals"], 38108649668),
              "dependencies": (b["dependencies"], 38108708826),
              "inventory": (c["inventory"], "new_targeted_free_model")}
    ledger = []
    for name in IDS:
        row, run = chosen[name]
        ledger.append({
            "task_id": name, "verified_run": run, "passed": row["passed"],
            "possible": row["total"], "status": row["status"],
            "known_buggy_baseline_passed": row["baseline_passed"],
            "candidate_proposed": row["status"] == "evaluated",
        })
    aggregate = {
        "schema": "bean.autonomy.lab021b.transfer.v1",
        "seed_phase": "final",
        "cases": sum(x["possible"] for x in ledger),
        "candidate_passes": sum(x["passed"] for x in ledger),
        "baseline_passes": sum(x["known_buggy_baseline_passed"] for x in ledger),
        "completely_solved_domains": sum(x["passed"] == x["possible"] for x in ledger),
        "domains_total": len(IDS),
        "tasks": ledger,
        "limitations": [
            "Task choices were researcher-provided, not autonomously discovered from an unknown codebase",
            "Provider models are external; BEAN orchestrates them without changing model weights",
            "GitHub artifacts and source receipts supply continuity; this is not new learned neural weights",
            "The evaluator is public in the repository but absent from every model prompt",
            "A passing score here alone cannot validate 8/10 broad autonomy",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return aggregate


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--b", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("compile")
    c.add_argument("--a", type=Path, required=True)
    c.add_argument("--b", type=Path, required=True)
    c.add_argument("--c", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = (prepare(args.a, args.b, args.out) if args.command == "prepare"
              else compile_results(args.a, args.b, args.c, args.out))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
