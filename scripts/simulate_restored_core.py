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
import random
from pathlib import Path
import shutil
import sys
import tempfile

# Running a script by filename puts scripts/ on sys.path, not the repo root.
# Match the proven import bootstrap in scripts/invoke_bean.py.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bean.evaluation.active_abstraction_benchmark import World
from bean.evaluation.github_digital_cycle import BLIND, FAMILIES, _hash, _prior_evaluations, run_scored_digital_cycle
from bean.learning.reasoning_service import NativeReasoningService
from scripts.invoke_bean import invoke, unpack


def evaluation_rows(db_path: Path) -> list[dict]:
    service = NativeReasoningService(db_path, model=None)
    try:
        return _prior_evaluations(service)
    finally:
        service.close()



def coverage_metrics(families: dict, cases_per_family: int = 48) -> dict:
    """Measure all arms on identical denominators, retaining missing ablations.

    Historical generations may lack a memory-ablated control. Do not convert
    absent evidence to zero accuracy or pretend it was scored.
    """
    if set(families) != set(FAMILIES):
        raise ValueError("missing or unexpected scored family")
    result = {}
    for arm in ("candidate", "grammar_matched", "passive", "memory_ablated", "shuffled", "always_zero"):
        correct = 0
        attempted = 0
        per_family = {}
        missing = False
        for family in FAMILIES:
            row = families[family]
            hits = row["correct"].get(arm)
            abstained = (0 if arm == "always_zero"
                         else row["abstentions"].get(arm))
            if hits is None or abstained is None:
                if arm not in ("memory_ablated", "grammar_matched"):
                    raise ValueError("missing required control measurement")
                missing = True
                per_family[family] = {"status": "Unknown", "correct": None,
                                      "attempted": None, "coverage": None,
                                      "accuracy_when_attempted": None}
                continue
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
            "correct": None if missing else correct,
            "attempted": None if missing else attempted,
            "coverage": None if missing else attempted / total,
            "accuracy_when_attempted": (
                None if missing or not attempted else correct / attempted),
            "all_case_accuracy": None if missing else correct / total,
            "status": "Unknown" if missing else "measured",
            "families": per_family,
        }
    return result


def nonlearning_controls(generation: int) -> dict:
    """Score fixed-label and pre-seeded random actions on blind worlds.

    This is an evaluator-only diagnostic computed AFTER real BEAN Core learning,
    not extra training, a new journal, or an oracle/majority-label policy. All
    controls attempt every case and use zero reward calls and zero fitting.
    The established all-zero comparator is retained separately in Core receipts.
    """
    if type(generation) is not int or generation < 1:
        raise ValueError("invalid simulation generation")
    controls = ("always_negative", "always_positive", "uniform_random")
    totals = {name: 0 for name in controls}
    families = {}
    for family_index, family in enumerate(FAMILIES):
        world_id = 100000 + generation * 100 + family_index
        world = World(world_id, family)
        rng = random.Random(world_id * 8191 + 17)
        ground_truth = [world.correct_action(case) for case in BLIND]
        counts = {str(label): ground_truth.count(label) for label in (-1, 0, 1)}
        scores = {
            "always_negative": counts["-1"],
            "always_positive": counts["1"],
            "uniform_random": sum(
                rng.choice((-1, 0, 1)) == truth for truth in ground_truth),
        }
        if sum(counts.values()) != len(BLIND):
            raise AssertionError("invalid blind truth-label partition")
        for name in controls:
            if not 0 <= scores[name] <= len(BLIND):
                raise AssertionError("invalid nonlearning control score")
            totals[name] += scores[name]
        families[family] = {
            "world_id": world_id,
            "blind_truth_label_counts": counts,
            "correct": scores,
            "attempted": len(BLIND),
        }
    return {
        "mode": "evaluator_only_post_learning",
        "probes_or_reward_calls": 0,
        "seed_rule": "world_id * 8191 + 17",
        "all_case_attempts_per_control": len(BLIND) * len(FAMILIES),
        "correct_totals": totals,
        "families": families,
        "note": "No training-derived majority label; fixed and uniform-random baselines, not AGI evidence.",
    }


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
                    for name in ("candidate", "grammar_matched", "passive", "memory_ablated", "shuffled", "always_zero")
                },
                "candidate_minus_grammar_matched": (\n                    None if digital.get("grammar_matched_correct_total") is None\n                    else digital["candidate_correct_total"] - digital["grammar_matched_correct_total"]),\n                "candidate_minus_passive": (
                    digital["candidate_correct_total"] -
                    digital["passive_correct_total"]),
                "families": digital["families"],
                "coverage_metrics": coverage_metrics(digital["families"]),
                "nonlearning_controls": nonlearning_controls(receipt["generation"]),
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
        for archive_name, original_hash in compressed_hashes.items():
            if sha256((source / archive_name).read_bytes()).hexdigest() != original_hash:
                raise AssertionError("source checkpoint archive was modified")

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
