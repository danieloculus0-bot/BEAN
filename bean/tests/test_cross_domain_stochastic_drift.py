"""Seeded stochastic stress test for BEAN's toy cross-domain feedback gates.

python -m unittest -v bean.tests.test_cross_domain_stochastic_drift
python -m bean.tests.test_cross_domain_stochastic_drift --report

Synthetic Monte Carlo, NOT a deployed policy, externally sourced task corpus,
model learning, or AGI evidence. Reuses native retrieval/SQLite journal replay.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
import random
import sys
import unittest

from bean.tests.test_cross_domain_negative_transfer import SEEDS, _cohort, _opposite
from bean.tests.test_cross_domain_feedback_gate import _split, _choose, _predict
from bean.tests.test_cross_domain_drift_probes import PROBE_INDICES

SCHEMA = "bean.synthetic_stochastic_drift_stress.v1"
SEED_START = 202611020301
TRIALS = 32
SCENARIOS = (
    "stationary_aligned_noisy", "stationary_inverted_noisy",
    "abrupt_reversal_noisy", "gradual_reversal_noisy", "uninformative_ood",
)
POLICIES = (
    "no_retrieval", "naive_copy", "frozen_feedback_gate",
    "two_error_probe_gate", "one_error_probe_gate",
)
COST_PER_LABEL = 0.25  # Declared utility sensitivity, not a real price.


def _match_probability(scenario, index):
    if scenario == "stationary_aligned_noisy":
        return 0.8
    if scenario == "stationary_inverted_noisy":
        return 0.2
    if scenario == "abrupt_reversal_noisy":
        return 0.8 if index < 10 else 0.2
    if scenario == "gradual_reversal_noisy":
        return 0.8 - 0.6 * index / 19
    if scenario == "uninformative_ood":
        return 0.5
    raise ValueError("unknown synthetic scenario")


def _target(source, probability, rng):
    return source if rng.random() < probability else _opposite(source)


def _update(orientation, errors, decision, observed, threshold):
    errors = errors + 1 if decision != observed else 0
    switched = False
    if errors >= threshold:
        orientation = "invert" if orientation == "copy" else "copy"
        errors = 0
        switched = True
    return orientation, errors, switched


def _replay(initial, rows, threshold):
    """Rebuild toy detector state solely from ordered disclosed probe receipts."""
    orientation, errors, switches = initial, 0, []
    name = "two_error_probe_gate" if threshold == 2 else "one_error_probe_gate"
    for row in rows:
        if row["orientation_before"][name] != orientation:
            raise AssertionError("replay orientation before feedback diverged")
        observed = row["feedback_observed"]
        if observed is not None:
            orientation, errors, switched = _update(
                orientation, errors, row["decisions_before_feedback"][name],
                observed, threshold)
            if switched:
                switches.append(row["stream_index"])
        if row["orientation_after"][name] != orientation:
            raise AssertionError("replay orientation after feedback diverged")
    return orientation, errors, switches


def _trial(calibration, heldout, scenario, seed):
    # Independent scorer PRNG; non-probe outcomes never reach the toy policies.
    material = f"{SCHEMA}:{scenario}:{seed}".encode("utf-8")
    rng = random.Random(int.from_bytes(sha256(material).digest()[:8], "big"))
    feedback = []
    for row in calibration:
        source = row["copied_action"]
        feedback.append({
            "case_id": row["case_id"],
            "source_lesson_id": row["source_lesson_id"],
            "source_action": source,
            "observed_target": _target(source, _match_probability(scenario, 0), rng),
        })
    initial = _choose(feedback)
    states = {"two_error_probe_gate": initial, "one_error_probe_gate": initial}
    streaks = {name: 0 for name in states}
    switches = {name: [] for name in states}
    cases = []
    for index, row in enumerate(heldout):
        source = row["copied_action"]
        before = dict(states)
        decisions = {
            "no_retrieval": "hold",
            "naive_copy": source,
            "frozen_feedback_gate": _predict(source, initial),
            **{name: _predict(source, states[name]) for name in states},
        }
        # Predictions are fixed before sampling the scorer-owned hidden target.
        truth = _target(source, _match_probability(scenario, index), rng)
        probe = index in PROBE_INDICES
        if probe:
            for name, threshold in (("two_error_probe_gate", 2),
                                    ("one_error_probe_gate", 1)):
                states[name], streaks[name], switched = _update(
                    states[name], streaks[name], decisions[name], truth, threshold)
                if switched:
                    switches[name].append(index)
        event = {
            "case_id": row["case_id"],
            "source_lesson_id": row["source_lesson_id"],
            "evidence_ref": row["evidence_ref"],
            "lexical_tie_count": row["tie_count"],
            "stream_index": index,
            "is_feedback_probe": probe,
            "orientation_before": before,
            "decisions_before_feedback": decisions,
            "feedback_observed": truth if probe else None,
            "orientation_after": dict(states),
            "scorer_only_target": truth,
            "correct": {name: action == truth for name, action in decisions.items()},
        }
        event["receipt_sha256"] = sha256(json.dumps(
            event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        cases.append(event)
    scored = [row for row in cases if not row["is_feedback_probe"]]
    scores = {name: sum(row["correct"][name] for row in scored)
              for name in POLICIES}
    label_costs = {"no_retrieval": 0, "naive_copy": 0,
                   "frozen_feedback_gate": len(feedback),
                   "two_error_probe_gate": len(feedback) + len(PROBE_INDICES),
                   "one_error_probe_gate": len(feedback) + len(PROBE_INDICES)}
    for name, threshold in (("two_error_probe_gate", 2),
                            ("one_error_probe_gate", 1)):
        if _replay(initial, cases, threshold) != (
                states[name], streaks[name], switches[name]):
            raise AssertionError("full feedback replay changed")
        # Simulated midstream restart, with pending error streak preserved.
        orientation, errors, _ = _replay(initial, cases[:10], threshold)
        for event in cases[10:]:
            if event["orientation_before"][name] != orientation:
                raise AssertionError("restart prefix/suffix mismatch")
            if event["feedback_observed"] is not None:
                orientation, errors, _ = _update(
                    orientation, errors, event["decisions_before_feedback"][name],
                    event["feedback_observed"], threshold)
        if (orientation, errors) != (states[name], streaks[name]):
            raise AssertionError("restart continuation lost error streak")
    return {
        "seed": seed, "scenario": scenario, "calibration": feedback,
        "scored_count": len(scored), "probe_indices": list(PROBE_INDICES),
        "scores": scores, "labels_consumed": label_costs,
        "net_utility": {name: scores[name] - COST_PER_LABEL * label_costs[name]
                        for name in POLICIES},
        "switches": switches, "cases": cases,
    }


def _summarize(trials):
    n = len(trials)
    summaries = {}
    for name in POLICIES:
        scores = [trial["scores"][name] for trial in trials]
        utilities = [trial["net_utility"][name] for trial in trials]
        summaries[name] = {
            "mean_correct_out_of_16": round(sum(scores) / n, 5),
            "min_correct_out_of_16": min(scores),
            "mean_net_utility": round(sum(utilities) / n, 5),
            "labels_per_trial": trials[0]["labels_consumed"][name],
        }
    for name in ("two_error_probe_gate", "one_error_probe_gate"):
        delta = [trial["scores"][name] - trial["scores"]["frozen_feedback_gate"]
                 for trial in trials]
        mean = sum(delta) / n
        variance = sum((v - mean) ** 2 for v in delta) / (n - 1)
        summaries[name]["paired_vs_frozen"] = {
            "mean_delta_correct": round(mean, 5),
            "descriptive_normal_95pct_interval": [
                round(mean - 1.96 * math.sqrt(variance / n), 5),
                round(mean + 1.96 * math.sqrt(variance / n), 5),
            ],
            "wins": sum(v > 0 for v in delta),
            "losses": sum(v < 0 for v in delta),
            "ties": sum(v == 0 for v in delta),
            "mean_switches": round(sum(len(t["switches"][name])
                                       for t in trials) / n, 5),
        }
    return summaries


def run_report():
    # Existing _cohort invokes real NativeReasoningService and checks SQLite
    # ExperienceBank close/reopen plus SHA-chained source retrieval replay.
    source = _cohort("aligned", SEEDS["aligned"])
    calibration, heldout = _split(source)
    scenarios = {}
    for scenario in SCENARIOS:
        trials = [_trial(calibration, heldout, scenario, SEED_START + i)
                  for i in range(TRIALS)]
        scenarios[scenario] = {
            "trials": trials, "summary": _summarize(trials),
        }
    payload = json.dumps(scenarios, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "source_cohort_seed": SEEDS["aligned"],
        "heldout_seeds": [SEED_START + i for i in range(TRIALS)],
        "scenario_match_probabilities": {
            name: [_match_probability(name, i) for i in range(20)]
            for name in SCENARIOS},
        "calibration_labels": len(calibration),
        "stream_feedback_labels": len(PROBE_INDICES),
        "scored_cases_per_trial": len(heldout) - len(PROBE_INDICES),
        "synthetic_source_restart_verified": True,
        "feedback_state_replay_from_receipts_verified": True,
        "feedback_label_cost_per_observation": COST_PER_LABEL,
        "scenarios": scenarios,
        "case_sha256": sha256(payload.encode()).hexdigest(),
        "limitations": [
            "All targets are generated from disclosed stochastic toy distributions",
            "Held-out Monte Carlo seeds are not independently sourced external tasks",
            "Intervals describe synthetic seeds, not human/device performance",
            "Toy gates do not learn semantic analogy, model weights, or general abilities",
            "Restart checks replay toy policy receipts, not a deployed persisted gate",
            "Native SQLite/SHA journal restart is verified only for source retrieval",
            "No Jetson, model inference, production event writes, or real-world costs",
        ],
    }


class StochasticDriftStressControls(unittest.TestCase):
    def test_disjoint_prequential_budget_and_replay(self):
        report = run_report()
        self.assertEqual(report["calibration_labels"], 4)
        self.assertEqual(report["stream_feedback_labels"], 4)
        self.assertEqual(report["scored_cases_per_trial"], 16)
        for scenario in report["scenarios"].values():
            self.assertEqual(len(scenario["trials"]), TRIALS)
            for trial in scenario["trials"]:
                cases = trial["cases"]
                self.assertEqual(len(cases), 20)
                self.assertFalse({r["case_id"] for r in trial["calibration"]} &
                                 {r["case_id"] for r in cases})
                self.assertEqual(sum(r["is_feedback_probe"] for r in cases), 4)
                self.assertTrue(all(r["lexical_tie_count"] == 1 and
                                    r["evidence_ref"].startswith("fixture:") and
                                    len(r["receipt_sha256"]) == 64 for r in cases))
                self.assertTrue(all((r["feedback_observed"] is not None) ==
                                    r["is_feedback_probe"] for r in cases))
                self.assertEqual(set(trial["scores"]), set(POLICIES))
                self.assertEqual(trial["labels_consumed"]["two_error_probe_gate"], 8)
        self.assertTrue(report["feedback_state_replay_from_receipts_verified"])

    def test_no_assumed_gain_and_negative_evidence(self):
        report = run_report()
        for scenario in report["scenarios"].values():
            for policy in POLICIES:
                self.assertTrue(0 <= scenario["summary"][policy]["mean_correct_out_of_16"] <= 16)
            for name in ("two_error_probe_gate", "one_error_probe_gate"):
                comparison = scenario["summary"][name]["paired_vs_frozen"]
                self.assertEqual(comparison["wins"] + comparison["losses"] +
                                 comparison["ties"], TRIALS)
        # Preserve losses; do not hard-code a claimed improvement.
        self.assertTrue(any(
            s["summary"]["one_error_probe_gate"]["paired_vs_frozen"]["losses"] > 0
            for s in report["scenarios"].values()))

    def test_deterministic_roundtrip(self):
        a, b = run_report(), run_report()
        self.assertEqual(a["case_sha256"], b["case_sha256"])
        self.assertEqual(json.loads(json.dumps(a)), a)


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
