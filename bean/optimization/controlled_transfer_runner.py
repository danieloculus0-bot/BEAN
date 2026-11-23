"""Execute a declared five-arm Python transfer experiment with durable receipts.

The external manifest defines tasks and sources. This does not generate novel
tasks, certify holdout independence, or invoke a language model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
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
    seen_skills = set()
    for task in spec["tasks"]:
        if not isinstance(task, dict) or not isinstance(task.get("skill"), str) or not task["skill"]:
            raise ValueError("each task requires a skill identity")
        if task["skill"] in seen_skills:
            raise ValueError("duplicate skill identity would corrupt matched controls")
        seen_skills.add(task["skill"])
        if not isinstance(task.get("tests"), str) or not task["tests"]:
            raise ValueError("each task requires a test file path")
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
    # Pin every input before the first arm. Evaluator code can alter files on
    # disk, so later arms must never silently consume changed tests or sources.
    pinned = {}
    for _, _, source, tests in planned:
        for path in (source, tests):
            resolved = path.resolve()
            pinned[resolved] = hashlib.sha256(resolved.read_bytes()).hexdigest()
    # Refuse a reused experiment identity before executing any code. Otherwise
    # prior receipts can silently contaminate a new matched-control summary.
    ledger_path = Path(database)
    if ledger_path.exists():
        if not ledger_path.is_file() or ledger_path.is_symlink():
            raise ValueError("ledger must be a regular file")
        previous = verify_reuse_outcomes(ledger_path)
        if any(row.get("experiment_id") == experiment_id for row in previous):
            raise ValueError("experiment_id already exists in outcome ledger")
    # Randomize evaluation order with a local seeded generator to reduce
    # systematic candidate-first order effects; retain condition labels.
    random.Random(seed).shuffle(planned)
    # Prevalidate all paths before running any evaluator.
    receipts = []
    for task, arm, source, tests in planned:
        if any(hashlib.sha256(path.read_bytes()).hexdigest() != digest
               for path, digest in pinned.items()):
            raise ValueError("experiment input drift detected; partial receipts retained")
        result = evaluate_python_skill(
            database, skill=task["skill"], source_file=source,
            tests_file=tests, experiment_id=experiment_id, condition=arm,
            model_id=model_id, seed=seed, timeout_seconds=timeout,
            novel_test_set=task.get("novel_test_set", False),
        )
        receipts.append({"skill": task["skill"], "condition": arm,
                         "passed": result["passed"], "receipt": result["receipt"]})
        if any(hashlib.sha256(path.read_bytes()).hexdigest() != digest
               for path, digest in pinned.items()):
            raise ValueError("experiment input drift detected; partial receipts retained")
    # Disclose whether control implementations are actually distinct. Matching
    # source bytes cannot support a claim of candidate superiority, even if
    # the manifest assigns different condition names. Do not reject ties: they
    # are useful negative controls and must remain observable.
    source_fingerprints = {task["skill"]: {arm: pinned[source.resolve()]
                           for t, arm, source, _ in planned if t is task}
                           for task, _, _, _ in planned}
    control_diversity = {skill: {
        "distinct_source_count": len(set(hashes.values())),
        "candidate_equals_strong_control": hashes["candidate"] == hashes["strong_control"],
        "candidate_equals_grammar_matched": hashes["candidate"] == hashes["grammar_matched"],
        "all_sources_identical": len(set(hashes.values())) == 1,
    } for skill, hashes in source_fingerprints.items()}
    # Require a new interpreter to recover and verify the persisted receipts.
    # An in-process cache or transient result cannot satisfy this check.
    ledger = str(Path(database).resolve())
    # The independent expectation comes from the return values captured
    # after each arm, not from re-reading the potentially rewritten ledger.
    # Receipt hashes commit to the complete outcome payload and chain head.
    expected = sorted(
        (r["receipt"]["sequence"], r["receipt"]["prior_sha256"],
         r["receipt"]["receipt_sha256"], r["skill"], r["condition"], r["passed"])
        for r in receipts
    )
    probe = """
import json, sqlite3, sys
from bean.optimization.reuse_outcome_ledger import verify_reuse_outcomes
rows = verify_reuse_outcomes(sys.argv[1])
with sqlite3.connect(sys.argv[1]) as db:
    chain = db.execute(
        "SELECT sequence, prior_sha256, receipt_sha256 "
        "FROM reuse_outcomes ORDER BY sequence"
    ).fetchall()
if len(rows) != len(chain):
    raise RuntimeError("ledger count drift")
result = sorted(
    (sequence, prior, digest, payload["skill"], payload["condition"], payload["passed"])
    for payload, (sequence, prior, digest) in zip(rows, chain)
    if payload.get("experiment_id") == sys.argv[2]
)
print(json.dumps(result))
"""
    restarted = subprocess.run(
        [sys.executable, "-c", probe, ledger, experiment_id],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if restarted.returncode != 0:
        raise RuntimeError("separate-process ledger verification failed; receipts retained")
    try:
        recovered = json.loads(restarted.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("separate-process ledger verification produced invalid evidence") from exc
    # JSON decodes tuples as lists. Do not silently accept changed payloads,
    # sequence numbers or a chain that was recomputed after the arm returned.
    if recovered != [list(row) for row in expected]:
        raise RuntimeError("separate-process ledger verification mismatch; receipts retained")
    summary = summarize_matched_experiment(verify_reuse_outcomes(database), experiment_id)
    return {"experiment_id": experiment_id, "receipts": receipts, "summary": summary,
            "independent_learning_verified": False, "model_invoked_by_runner": False,
            "separate_process_ledger_verified": True,
            "control_diversity": control_diversity}


def main(argv=None):
    parser = argparse.ArgumentParser(description="BEAN controlled skill-transfer evaluator")
    parser.add_argument("manifest")
    parser.add_argument("database")
    args = parser.parse_args(argv)
    print(json.dumps(run_manifest(args.manifest, args.database), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
