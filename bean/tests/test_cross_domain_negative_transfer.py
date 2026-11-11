"""Matched-budget synthetic test of cross-domain *negative* transfer.

Run: python -m unittest bean.tests.test_cross_domain_negative_transfer
Case receipts: python -m bean.tests.test_cross_domain_negative_transfer --report

This evaluates a deterministic, intentionally naive "copy the top recalled
procedure" policy, NOT a language model or BEAN's actual decision policy.
Targets are withheld from retrieval and scored by an independent toy oracle.
No live device, company data, external provider, or new memory backend.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService

SCHEMA = "bean.synthetic_negative_transfer.v1"
COUNT = 24
SEEDS = {"aligned": 2026110201, "adversarial_ood": 2026110202}


def _opposite(action):
    return "flip" if action == "hold" else "hold"


def _cohort(name, seed):
    """One frozen paired cohort; both policies face identical hidden labels."""
    rng = random.Random(seed)
    actions = ["hold"] * (COUNT // 2) + ["flip"] * (COUNT // 2)
    rng.shuffle(actions)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "native_reasoning.sqlite"
        core = NativeReasoningService(db, model=None)
        for index, source_action in enumerate(actions):
            # Non-overlapping lexical keys; OOD changes the source vocabulary.
            prefix_a, prefix_b = (("beacon", "latch") if name == "adversarial_ood"
                                  else ("token", "gate"))
            tag_a = f"{prefix_a}{seed}x{index}"
            tag_b = f"{prefix_b}{seed}x{index}"
            query = f"{tag_a} {tag_b}"
            source_domain = f"fictional-source-{name}-{index}"
            target_domain = f"fictional-target-{name}-{index}"
            ref = f"fixture:{name}:{index}"
            lesson = core.retain_skill(
                domain=source_domain, name=query,
                steps=[f"Choose {source_action}"],
                passed=True, evidence_refs=[ref])["lesson_id"]
            # The independent target oracle is never passed to the retriever.
            truth = (source_action if name == "aligned"
                     else _opposite(source_action))
            matches = core.recall_analogies(
                domain=target_domain, query=query, limit=1)
            if len(matches) != 1:
                raise AssertionError(f"Expected exactly one lexical hit: {index}")
            hit = matches[0]
            if (hit["lesson_id"] != lesson or hit["evidence_refs"] != [ref]
                    or hit["lexical_tie_count"] != 1
                    or hit["independently_verified_transfer"] is not False):
                raise AssertionError("Precedent provenance/uncertainty changed")
            # A deliberately simplistic copy policy, not a real model response.
            text = hit["text"]
            if "Choose hold" in text:
                copied = "hold"
            elif "Choose flip" in text:
                copied = "flip"
            else:
                raise AssertionError("Unrecognized synthetic source procedure")
            rows.append({
                "case_id": f"{name}-{index:02d}",
                "query": query,
                "source_lesson_id": lesson,
                "evidence_ref": ref,
                "source_action": source_action,
                "target_oracle_action": truth,
                "baseline_action": "hold",
                "copied_action": copied,
                "baseline_correct": truth == "hold",
                "copy_correct": copied == truth,
                "tie_count": hit["lexical_tie_count"],
            })
        before = len(core.bank.journal.events())
        core.close()
        reopened = NativeReasoningService(db, model=None)
        try:
            for row in rows:
                replay = reopened.recall_analogies(
                    domain=f"fictional-target-{name}-{int(row['case_id'].split('-')[-1])}",
                    query=row["query"], limit=1)
                if len(replay) != 1 or replay[0]["lesson_id"] != row["source_lesson_id"]:
                    raise AssertionError("SQLite restart/replay changed retrieval")
            if len(reopened.bank.journal.events()) != before:
                raise AssertionError("Read-only replay wrote to the reasoning journal")
        finally:
            reopened.close()
    return rows


def run_report():
    cohorts = {}
    for name, seed in SEEDS.items():
        rows = _cohort(name, seed)
        canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
        cohorts[name] = {
            "seed": seed, "cases": len(rows),
            "baseline_correct": sum(row["baseline_correct"] for row in rows),
            "copy_correct": sum(row["copy_correct"] for row in rows),
            "negative_transfer_cases": [
                row["case_id"] for row in rows
                if row["baseline_correct"] and not row["copy_correct"]
            ],
            "case_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
            "cases_detail": rows,
            "restart_replay_verified": True,
        }
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "policy": "naive_copy_top_lexical_hit_not_native_model",
        "baseline": "constant_hold",
        "independent_oracle": "synthetic_target_action_hidden_from_retrieval",
        "fixed_retrieval_budget": 1,
        "cohorts": cohorts,
        "limitations": [
            "Synthetic deliberately controlled source-target relationship",
            "No trained model, actual policy learning, or Jetson execution",
            "The source labels are generated, not independently acquired abilities",
            "Success in aligned cohort is by construction; OOD failure is a counterexample",
        ],
    }


class NegativeTransferControls(unittest.TestCase):
    def test_frozen_paired_cohorts_and_restart(self):
        report = run_report()
        aligned = report["cohorts"]["aligned"]
        adversarial = report["cohorts"]["adversarial_ood"]
        self.assertEqual((aligned["baseline_correct"], aligned["copy_correct"]),
                         (12, 24))
        self.assertEqual((adversarial["baseline_correct"], adversarial["copy_correct"]),
                         (12, 0))
        self.assertEqual(len(adversarial["negative_transfer_cases"]), 12)
        for cohort in (aligned, adversarial):
            self.assertEqual(cohort["cases"], COUNT)
            self.assertTrue(cohort["restart_replay_verified"])
            self.assertEqual(len(cohort["case_sha256"]), 64)
            self.assertTrue(all(row["tie_count"] == 1
                                for row in cohort["cases_detail"]))

    def test_reproducible_case_hashes(self):
        first = run_report()
        second = run_report()
        self.assertEqual(
            {key: val["case_sha256"] for key, val in first["cohorts"].items()},
            {key: val["case_sha256"] for key, val in second["cohorts"].items()})


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
