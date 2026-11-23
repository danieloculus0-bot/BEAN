"""Execute a declared five-arm Python transfer experiment with durable receipts.

The external manifest defines tasks and sources. This does not generate novel
tasks, certify holdout independence, or invoke a language model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bean.optimization.metered_reuse_evaluator import evaluate_python_skill
from bean.optimization.reuse_outcome_ledger import (
    summarize_matched_experiment, verify_reuse_outcomes,
)

ARMS = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")


def run_manifest(manifest_file, database):
    manifest = Path(manifest_file).resolve()
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or not isinstance(spec.get("tasks"), list) or not spec["tasks"]:
        raise ValueError("nonempty tasks list required")
    experiment_id, model_id, seed = (spec.get(k) for k in ("experiment_id", "model_id", "seed"))
    timeout = spec.get("timeout_seconds", 30)
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id required")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model_id required; use 'none' for non-model experiments")
    if type(seed) is not int or seed < 0:
        raise ValueError("nonnegative integer seed required")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
        raise ValueError("invalid timeout")
    planned = []
    for task in spec["tasks"]:
        if not isinstance(task, dict) or not isinstance(task.get("skill"), str) or not task["skill"]:
            raise ValueError("each task requires a skill identity")
        if type(task.get("novel_test_set", False)) is not bool:
            raise ValueError("novel_test_set must be boolean")
        sources = task.get("sources")
        if not isinstance(sources, dict) or set(sources) != set(ARMS):
            raise ValueError("each task requires exactly five named control sources")
        tests = manifest.parent / task["tests"]
        if not tests.is_file():
            raise ValueError("missing test file")
        for arm in ARMS:
            source = manifest.parent / sources[arm]
            if not source.is_file() or source.resolve() == tests.resolve():
                raise ValueError("missing or identical source/test file")
            planned.append((task, arm, source, tests))
    # Prevalidate all paths before running any evaluator.
    receipts = []
    for task, arm, source, tests in planned:
        result = evaluate_python_skill(
            database, skill=task["skill"], source_file=source,
            tests_file=tests, experiment_id=experiment_id, condition=arm,
            model_id=model_id, seed=seed, timeout_seconds=timeout,
            novel_test_set=task.get("novel_test_set", False),
        )
        receipts.append({"skill": task["skill"], "condition": arm,
                         "passed": result["passed"], "receipt": result["receipt"]})
    summary = summarize_matched_experiment(verify_reuse_outcomes(database), experiment_id)
    return {"experiment_id": experiment_id, "receipts": receipts, "summary": summary,
            "independent_learning_verified": False, "model_invoked_by_runner": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="BEAN controlled skill-transfer evaluator")
    parser.add_argument("manifest")
    parser.add_argument("database")
    args = parser.parse_args(argv)
    print(json.dumps(run_manifest(args.manifest, args.database), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
