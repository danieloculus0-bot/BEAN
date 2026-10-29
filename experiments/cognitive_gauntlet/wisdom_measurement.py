"""Five-dimension, prequential audit of the existing frozen gauntlet.

This measures concrete proxies, not intelligence or wisdom itself. Decisions,
state traces and original receipts remain unchanged; scores are post-hoc.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math
from .decision_audit import audit_cases
from .sensor_reliability import OnlineSensorTrust, SensorObservation

ARMS = ("fixed_prior", "long_memory", "forgetful", "unweighted", "schrodingers_logic")
WISDOM_SCHEMA = "bean.gauntlet.wisdom_measurement.v1"


def _average(values):
    return sum(values) / len(values) if values else None


def measure(report):
    """Score *all* cases, including mistakes; reject missing or corrupt cases."""
    if not isinstance(report, dict) or not isinstance(report.get("cases"), list):
        raise ValueError("complete benchmark report required")
    cases = report["cases"]
    if not cases or not isinstance(report.get("reference_digest"), str):
        raise ValueError("source evidence digest required")
    audit = audit_cases(cases, ARMS, source_digest=report["reference_digest"])
    groups = {}
    outcomes = defaultdict(list)
    trust_scores = defaultdict(lambda: defaultdict(list))
    alternatives = defaultdict(lambda: {"cases": 0, "disagreements": 0,
                                        "chaos_cases": 0, "hindsight_regret": []})
    last_step = defaultdict(lambda: -1)
    for case in cases:
        regime, seed, step = case["regime"], case["seed"], case["step"]
        key = (regime, seed)
        if step != last_step[key] + 1:
            raise ValueError("missing or reordered receipt")
        last_step[key] = step
        if key not in groups:
            groups[key] = (OnlineSensorTrust(), OnlineSensorTrust(decay=.97))
        long_state, short_state = groups[key]
        observations = [SensorObservation(**event) for event in case["evidence"]]
        if len(observations) != 5:
            raise ValueError("five source observations per decision required")
        outcome = case["truth_revealed_after_forecast"]
        # Reliability is read only BEFORE each delayed-feedback label is applied.
        for observation in observations:
            correct = int(observation.value == outcome)
            for name, estimate in (
                ("fixed_prior", .75),
                ("long_memory", long_state.reliability(observation.origin)),
                ("forgetful", short_state.reliability(observation.origin)),
            ):
                trust_scores[regime][name].append((estimate-correct)**2)
                trust_scores["all"][name].append((estimate-correct)**2)
        for name, learner in (("long_memory", long_state), ("forgetful", short_state)):
            prediction = learner.forecast(observations)
            if not math.isclose(prediction, case["predictions"][name],
                                abs_tol=1e-12, rel_tol=1e-12):
                raise ValueError("replayed source policy diverged")
        long_state.learn(outcome)
        short_state.learn(outcome)
        outcomes[regime].append(case)
        outcomes["all"].append(case)
        branches = alternatives[regime]
        combined = alternatives["all"]
        for stats in (branches, combined):
            stats["cases"] += 1
            stats["disagreements"] += int(
                abs(case["predictions"]["long_memory"] -
                    case["predictions"]["forgetful"]) >= .10)
            stats["chaos_cases"] += int(case["mode"] == "parallel_chaos")
            best_ex_post = min(case["losses"]["long_memory"],
                               case["losses"]["forgetful"])
            stats["hindsight_regret"].append(
                case["losses"]["schrodingers_logic"] - best_ex_post)
    if len(cases) != audit["overall"]["cases"]:
        raise ValueError("case coverage mismatch")

    evidence = {}
    options = {}
    learning = {}
    decision = {}
    for regime, rows in outcomes.items():
        n = len(rows)
        estimates = {name: _average(trust_scores[regime][name])
                     for name in ("fixed_prior", "long_memory", "forgetful")}
        evidence[regime] = {
            "sensor_observations": len(trust_scores[regime]["fixed_prior"]),
            "source_reliability_brier": estimates,
            "note": "Pre-feedback reliability versus subsequently revealed sensor correctness",
        }
        stats = alternatives[regime]
        options[regime] = {
            "cases_with_two_branches_evaluated": stats["cases"],
            "branch_disagreement_ge_0_10": stats["disagreements"],
            "chaos_parallel_decisions": stats["chaos_cases"],
            "mean_posthoc_regret_vs_best_branch": _average(stats["hindsight_regret"]),
        }
        decision[regime] = (audit["overall"] if regime == "all"
                            else audit["by_regime"][regime])
        first = [row for row in rows if row["step"] < report["rounds"]//4]
        last = [row for row in rows if row["step"] >= 3*report["rounds"]//4]
        def losses(batch):
            return {arm: _average([row["losses"][arm] for row in batch]) for arm in ARMS}
        learning[regime] = {
            "early_cases": len(first),
            "late_cases": len(last),
            "early_mse": losses(first),
            "late_mse": losses(last),
            "caution": "early/late is descriptive, not an isolated causal effect of learning",
        }
    swap = [row for row in cases if row["regime"] == "source_swap"]
    if swap:
        midpoint = report["rounds"]//2
        windows = {
            "immediately_after_swap": [r for r in swap if midpoint <= r["step"] < midpoint+10],
            "later_after_swap": [r for r in swap if r["step"] >= midpoint+20],
        }
        learning["source_swap"]["post_change_windows"] = {
            name: {arm: _average([row["losses"][arm] for row in rows]) for arm in ARMS}
            for name, rows in windows.items()
        }
    response = {
        "schema": WISDOM_SCHEMA,
        "source_digest": report.get("digest"),
        "reference_digest": report["reference_digest"],
        "cases_included": len(cases),
        "evaluation_type": "post-hoc measurement on reused synthetic scenarios, not new held-out tasks",
        "dimensions": {
            "alternative_reasoning": options,
            "evidence_judgment": evidence,
            "uncertainty_awareness": {
                k: {arm: {metric: data["arms"][arm][metric] for metric in
                           ("brier", "log_loss", "calibration_error_10bin", "high_confidence_mistakes")}
                    for arm in ARMS}
                for k, data in decision.items()},
            "decision_quality": {
                k: {arm: {metric: data["arms"][arm][metric] for metric in
                           ("classification_error", "decision_switches", "decision_cost_sensitivity")}
                    for arm in ARMS}
                for k, data in decision.items()},
            "learning_after_feedback": learning,
        },
        "limits": [
            "Branch count is not evidence of broad reasoning or consideration of every possible action.",
            "Labels are provided by a synthetic environment AFTER forecasts, not verified by BEAN.",
            "Hindsight regret scores only outcomes, not whether an ex-ante choice was defensible.",
            "No wall-clock thinking time or real deliberation latency is measured.",
            "All tested regimes are known synthetic families; no external AGI opponent executed.",
        ],
    }
    canonical = json.dumps(response, sort_keys=True, separators=(",", ":"), allow_nan=False)
    response["audit_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return response
