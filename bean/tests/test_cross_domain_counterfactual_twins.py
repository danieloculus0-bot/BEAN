"""Synthetic identifiability control for cross-domain precedent transfer.

Run: python -m unittest -v bean.tests.test_cross_domain_counterfactual_twins
Report: python -m bean.tests.test_cross_domain_counterfactual_twins --report

Uses the real native retrieval/restart exercise in the existing paired test.
Counterfactual target outcomes are deliberately constructed and never shown
as retrieval evidence. This is an impossibility control, not an AGI result.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest

from bean.tests.test_cross_domain_negative_transfer import COUNT, SEEDS, _cohort, _opposite

SCHEMA = "bean.synthetic_transfer_identifiability.v1"
VISIBLE = ("query", "source_lesson_id", "evidence_ref", "copied_action", "tie_count")


def _worlds(rows):
    """Counterfactual worlds share all observed evidence, not target labels."""
    pairs = []
    for row in rows:
        observed = {field: row[field] for field in VISIBLE}
        aligned = row["target_oracle_action"]
        if aligned != row["copied_action"]:
            raise AssertionError("Expected the source-aligned calibration world")
        pairs.append({
            "case_id": row["case_id"],
            "observable": observed,
            "world_a_target": aligned,
            "world_b_target": _opposite(aligned),
        })
    return pairs


def _action(observed, policy):
    """Frozen policies receive no target labels or world identifier."""
    if policy == "hold":
        return "hold"
    if policy == "copy":
        return observed["copied_action"]
    if policy == "tie_only":
        return observed["copied_action"] if observed["tie_count"] == 1 else "hold"
    if policy == "hash_control":
        digest = sha256(observed["query"].encode("utf-8")).digest()
        return "hold" if digest[0] % 2 == 0 else "flip"
    raise ValueError("Unknown policy")


def _evaluate(pairs):
    outcomes = {}
    for policy in ("hold", "copy", "tie_only", "hash_control"):
        a = b = 0
        for pair in pairs:
            decision = _action(pair["observable"], policy)
            a += decision == pair["world_a_target"]
            b += decision == pair["world_b_target"]
        outcomes[policy] = {"world_a_correct": a, "world_b_correct": b,
                            "pooled_correct": a + b, "pooled_cases": 2 * len(pairs)}
    return outcomes


def run_report():
    # _cohort performs real NativeReasoningService retrieval, verifies source
    # provenance, and reopens SQLite to check replay and journal invariance.
    rows = _cohort("aligned", SEEDS["aligned"])
    pairs = _worlds(rows)
    outcomes = _evaluate(pairs)
    canonical = json.dumps(pairs, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "source_cohort_seed": SEEDS["aligned"],
        "paired_worlds": len(pairs),
        "observable_fields": list(VISIBLE),
        "same_observation_both_worlds": True,
        "counterfactual_target_relation": "binary_opposites_by_construction",
        "outcomes": outcomes,
        "case_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        "cases_detail": pairs,
        "restart_replay_verified_by_source_cohort": True,
        "limitations": [
            "Synthetic counterfactual labels are constructed, not independently sampled",
            "No model or target-domain feedback is used by the frozen policies",
            "Only binary actions; indistinguishability does not imply every domain is ambiguous",
            "No real-world ability gain or deployed Jetson behavior is measured",
        ],
    }


class CounterfactualTwinControls(unittest.TestCase):
    def test_hidden_worlds_cannot_be_disambiguated_from_source_only(self):
        report = run_report()
        self.assertEqual(report["paired_worlds"], COUNT)
        self.assertEqual(len(report["cases_detail"]), COUNT)
        for pair in report["cases_detail"]:
            self.assertEqual(pair["world_b_target"], _opposite(pair["world_a_target"]))
            self.assertEqual(set(pair["observable"]), set(VISIBLE))
            self.assertEqual(pair["observable"]["tie_count"], 1)
        for outcome in report["outcomes"].values():
            self.assertEqual(outcome["pooled_correct"], COUNT)
            self.assertEqual(outcome["pooled_cases"], 2 * COUNT)
        self.assertEqual(report["outcomes"]["copy"]["world_a_correct"], COUNT)
        self.assertEqual(report["outcomes"]["copy"]["world_b_correct"], 0)

    def test_case_receipts_repeat_and_do_not_expose_hidden_world_to_policy(self):
        first = run_report()
        second = run_report()
        self.assertEqual(first["case_sha256"], second["case_sha256"])
        self.assertEqual(first["outcomes"], second["outcomes"])
        self.assertTrue(first["restart_replay_verified_by_source_cohort"])
        with self.assertRaises(ValueError):
            _action(first["cases_detail"][0]["observable"], "oracle")


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
