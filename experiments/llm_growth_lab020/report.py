"""Collect independent LAB020 evaluations; no LLM API credentials needed."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from experiments.llm_growth_lab020.lab020 import (
    SCHEMA, TARGET, score_candidate,
)


def make_report(*, artifacts: Path, source: Path, holdout: Path, out: Path) -> dict:
    artifacts = Path(artifacts)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ast_file = artifacts / "lab020-ast" / "ast-report.json"
    ast = json.loads(ast_file.read_text(encoding="utf-8")) if ast_file.is_file() else None
    rounds = []
    best = None
    seen = set()
    for idx in range(3):
        data = artifacts / ("lab020-eval" + str(idx)) / "feedback.json"
        if not data.is_file():
            rounds.append({"iteration": idx, "outcome": "not_run"})
            continue
        row = json.loads(data.read_text(encoding="utf-8"))
        if row["schema"] != SCHEMA or row["round"] != idx:
            raise ValueError("evaluation artifact did not match expected round")
        fingerprint = row.get("candidate_sha")
        trial = {
            "iteration": idx, "model_served": row.get("model"),
            "provider_status": row.get("status"),
            "candidate_sha": fingerprint,
            "dev_score": row["test"]["passed_tests"],
            "dev_total": row["test"]["total"],
            "outcome": row["outcome"],
            "duplicate_source": fingerprint in seen if fingerprint else False,
            "history_tip": row["history_tip"],
        }
        rounds.append(trial)
        if fingerprint:
            seen.add(fingerprint)
        if row["outcome"] == "validated":
            if best is None or trial["dev_score"] > best["dev_score"]:
                best = trial
    holdout_result = None
    if best is not None:
        candidate = artifacts / ("lab020-gen" + str(best["iteration"])) / "proposal.py"
        if not candidate.is_file():
            raise ValueError("selected candidate missing")
        holdout_result = score_candidate(candidate.read_text(encoding="utf-8"),
                                         test_source=holdout)
    baseline_holdout = score_candidate(source.read_text(encoding="utf-8"),
                                       test_source=holdout)
    verdict = ("LLM_REPAIR_VALIDATED_ON_FRESH_HOLDOUT" if holdout_result
               and holdout_result["passed"] and not baseline_holdout["passed"]
               else "GENERALIZATION_NOT_DEMONSTRATED")
    report = {"schema": SCHEMA, "real_core_target": TARGET,
              "live_trials": rounds, "ast_bruteforce": ast,
              "best_dev": best, "baseline_holdout": baseline_holdout,
              "fresh_holdout": holdout_result,
              "verdict": verdict,
              "no_model_weight_updates": True,
              "no_test_code_ever_sent_to_model": True,
              "holdout_independence_note": (
                  "Test files are excluded from model prompt, but are present "
                  "in a publicly accessible research branch, not externally sealed."),
              "all_promotions_require_independent_main_ci": True}
    (out / "lab020-final-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--source", type=Path, default=Path(TARGET))
    p.add_argument("--holdout", type=Path,
                   default=Path("experiments/llm_growth_lab020/test_selection_holdout.py"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = make_report(artifacts=args.artifacts, source=args.source,
                       holdout=args.holdout, out=args.out)
    print(json.dumps(data, indent=2, sort_keys=True))
    import os
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("verdict=" + data["verdict"] + "\n")
            if data["best_dev"] is not None:
                f.write("best_round=" + str(data["best_dev"]["iteration"]) + "\n")


if __name__ == "__main__":
    main()
