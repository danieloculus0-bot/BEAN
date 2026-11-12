#!/usr/bin/env python3
"""Execute real BEAN Core boots from a copy of its public synthetic checkpoint.

This is a bounded experiment on GitHub-hosted disposable runners. The existing
SQLite/SHA journals remain the only cognition store; no private state, paid
provider, external effectors, or main checkpoint mutation is involved.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

# Running a script by filename puts scripts/ on sys.path, not the repo root.
# Match the proven import bootstrap in scripts/invoke_bean.py.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bean.evaluation.github_digital_cycle import FAMILIES, _hash, _prior_evaluations, run_scored_digital_cycle
from bean.learning.reasoning_service import NativeReasoningService
from scripts.invoke_bean import invoke, unpack


def evaluation_rows(db_path: Path) -> list[dict]:
    service = NativeReasoningService(db_path, model=None)
    try:
        return _prior_evaluations(service)
    finally:
        service.close()



def coverage_metrics(families: dict, cases_per_family: int = 48) -> dict:
    """Report attempted-case accuracy separately from all-case accuracy.

    Historical SHA-linked receipts are read-only. This derives measurements
    solely for the disposable simulation artifact, never rewriting journals.
    """
    if set(families) != set(FAMILIES):
        raise ValueError("missing or unexpected scored family")
    result = {}
    for arm in ("candidate", "passive", "shuffled", "always_zero"):
        correct = 0
        attempted = 0
        per_family = {}
        for family in FAMILIES:
            row = families[family]
            hits = row["correct"][arm]
            abstained = (0 if arm == "always_zero"
                         else row["abstentions"][arm])
            if (type(hits) is not int or type(abstained) is not int
                    or not 0 <= abstained <= cases_per_family
                    or not 0 <= hits <= cases_per_family - abstained):
                raise ValueError("invalid accuracy or abstention counts")
            tries = cases_per_family - abstained
            per_family[family] = {
                "correct": hits, "attempted": tries,
                "coverage": tries / cases_per_family,
                "accuracy_when_attempted": hits / tries if tries else None,
            }
            correct += hits
            attempted += tries
        total = cases_per_family * len(FAMILIES)
        result[arm] = {
            "correct": correct, "attempted": attempted,
            "coverage": attempted / total,
            "accuracy_when_attempted": correct / attempted if attempted else None,
            "all_case_accuracy": correct / total,
            "families": per_family,
        }
    return result


def run_simulations(source: Path) -> dict:
    original_manifest_path = source / "manifest.json"
    raw_original = original_manifest_path.read_bytes()
    original = json.loads(raw_original)
    if original.get("synthetic_only") is not True:
        raise ValueError("refusing non-synthetic BEAN checkpoint")
    if original.get("generation") != original.get("boots"):
        raise ValueError("starting checkpoint continuity mismatch")

    with tempfile.TemporaryDirectory(prefix="bean-restored-paired-") as directory:
        root = Path(directory)
        state = root / "state"
        state.mkdir()
        shutil.copy2(original_manifest_path, state / "manifest.json")
        compressed_hashes = {}
        for db_record in original["databases"].values():
            name = db_record["archive"]
            if Path(name).name != name:
                raise ValueError("unsafe archive reference")
            path = source / name
            compressed_hashes[name] = sha256(path.read_bytes()).hexdigest()
            shutil.copy2(path, state / name)

        # Restore the exact current synthetic Core history, including its
        # retained native reasoning rules. Do not construct a blank brain.
        initial_runtime = root / "initial-restored"
        initial_runtime.mkdir()
        previous = unpack(state, initial_runtime)
        if previous["receipt_sha256"] != original["receipt_sha256"]:
            raise AssertionError("restored baseline receipt changed")
        initial_evaluations = evaluation_rows(
            initial_runtime / "bean_reasoning.sqlite3")
        starting_families = {
            row["family"]: row for row in initial_evaluations
            if row.get("generation") == original["generation"]
        }
        if set(starting_families) != set(FAMILIES):
            raise AssertionError("baseline lacks three scored families")

        results = []
        previous_manifest = original
        for trial_index in (1, 2):
            # The second fresh runtime proves complete process reconstruction
            # from the newly written synthetic archive, not just object reuse.
            runtime = root / f"isolated-core-boot-{trial_index}"
            receipt = invoke(state, runtime, ticks=12, hz=20)
            if receipt["generation"] != previous_manifest["generation"] + 1:
                raise AssertionError("generation continuity lost")
            if receipt["boots"] != previous_manifest["boots"] + 1:
                raise AssertionError("BEAN Core did not actually boot")
            if receipt["events"] <= previous_manifest["events"]:
                raise AssertionError("BEAN did not persist new events")
            if receipt["previous_receipt_sha256"] != previous_manifest["receipt_sha256"]:
                raise AssertionError("SHA receipt lineage broken")
            if receipt["processed_digital_commands"] < 2:
                raise AssertionError("BEAN Core commands not completed")
            digital = receipt["digital_learning"]
            if not digital["new_evaluation"] or digital["blind_cases_total"] != 144:
                raise AssertionError("fresh paired scoring did not run")
            if set(digital["families"]) != set(FAMILIES):
                raise AssertionError("missing digital learning family")
            if digital["source_evidence_sha256"] == previous_manifest.get(
                    "digital_learning", {}).get("source_evidence_sha256"):
                raise AssertionError("new world produced duplicate scoring evidence")
            if digital["independently_audited"] is not False:
                raise AssertionError("incorrect independent-audit claim")

            summary = {
                "generation": receipt["generation"],
                "boots": receipt["boots"],
                "events": receipt["events"],
                "receipt_sha256": receipt["receipt_sha256"],
                "previous_receipt_sha256": receipt["previous_receipt_sha256"],
                "source_sha": receipt["source_sha"],
                "source_evidence_sha256": digital["source_evidence_sha256"],
                "blind_cases_total": digital["blind_cases_total"],
                "correct": {
                    name: digital[f"{name}_correct_total"]
                    for name in ("candidate", "passive", "shuffled", "always_zero")
                },
                "candidate_minus_passive": (
                    digital["candidate_correct_total"] -
                    digital["passive_correct_total"]),
                "families": digital["families"],
                "coverage_metrics": coverage_metrics(digital["families"]),
            }
            for family, data in summary["families"].items():
                correct = data["prior_generation_transfer_correct"]
                attempted = data["prior_generation_transfer_attempted"]
                if correct is not None and attempted is not None:
                    if not 0 <= correct <= attempted <= 48:
                        raise AssertionError("invalid transfer numerator/denominator")
                if data["evaluation_sha256"] == starting_families[family][
                        "evaluation_sha256"]:
                    raise AssertionError("world evidence did not change")
            results.append(summary)
            previous_manifest = receipt

        # Restore the SECOND new checkpoint in a third clean runtime. Verify
        # its SHA-linked journal and ensure rescoring credits no case twice.
        recovery = root / "final-recovery"
        recovery.mkdir()
        restored = unpack(state, recovery)
        if restored["receipt_sha256"] != previous_manifest["receipt_sha256"]:
            raise AssertionError("final archived checkpoint does not replay")
        reasoning_db = recovery / "bean_reasoning.sqlite3"
        before = evaluation_rows(reasoning_db)
        for row_gen in (original["generation"] + 1, original["generation"] + 2):
            rows = [row for row in before if row.get("generation") == row_gen]
            if len(rows) != len(FAMILIES) or set(
                    row["family"] for row in rows) != set(FAMILIES):
                raise AssertionError("missing/repeated durable evaluation")
            for row in rows:
                if row["evaluation_sha256"] != _hash({
                        key: value for key, value in row.items()
                        if key != "evaluation_sha256"}):
                    raise AssertionError("case-level evidence hash mismatch")

        duplicate = run_scored_digital_cycle(
            reasoning_db,
            generation=restored["generation"],
            source_sha=restored["digital_learning"]["source_sha"])
        if duplicate["new_evaluation"] is not False:
            raise AssertionError("existing generation wrongly earned credit again")
        if evaluation_rows(reasoning_db) != before:
            raise AssertionError("duplicate evaluation altered journal")

        if (source / "manifest.json").read_bytes() != raw_original:
            raise AssertionError("source checkpoint manifest was modified")

        return {
            "schema": "bean.github.restored_core_paired_sim.v1",
            "scope": "public_synthetic_python_core_not_agi",
            "independent_external_validation": False,
            "benchmark": "active_abstraction_benchmark.World",
            "model_weights_trained": False,
            "original_generation": original["generation"],
            "original_receipt_sha256": original["receipt_sha256"],
            "original_manifest_sha256": sha256(raw_original).hexdigest(),
            "original_compressed_archive_sha256": compressed_hashes,
            "source_git_sha": os.environ.get("GITHUB_SHA", "local-validation"),
            "fresh_core_boots_executed": 2,
            "matched_learning_budget_probes": 12,
            "blind_cases_per_generation": 144,
            "new_world_generations": [row["generation"] for row in results],
            "generation_results": results,
            "second_checkpoint_restored_in_fresh_runtime_and_connections": True,
            "no_duplicate_scoring_after_restart": True,
            "original_checkpoint_unchanged": True,
            "limits": [
                "World is a synthetic repository-defined benchmark.",
                "New world seeds do not imply out-of-distribution general intelligence.",
                "Passive and shuffled controls are native existing evaluator controls.",
                "A tied or losing candidate remains a negative result.",
            ],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path,
                        default=Path("research/github_brain"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = run_simulations(args.state_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    for row in report["generation_results"]:
        print(json.dumps({
            "generation": row["generation"], "correct": row["correct"],
            "candidate_minus_passive": row["candidate_minus_passive"],
            "receipt_sha256": row["receipt_sha256"]}, sort_keys=True))
    print(json.dumps({
        "status": "restored_core_paired_simulation_completed",
        "original_generation": report["original_generation"],
        "restored_generations": report["new_world_generations"],
        "checkpoint_mutated": not report["original_checkpoint_unchanged"]},
        sort_keys=True))


if __name__ == "__main__":
    main()
