"""Outcome-based strategy arbitration for Lab026.

Borrow the *ideas* of Reflexion, Voyager and GEPA: evaluate candidate
reflection, reusable skill and instruction contexts before selecting one.
Selection evidence must be the recorded development/selection trial,
NEVER performance on held-out final tests.
"""
from __future__ import annotations

from .experimental import SCHEMA, material_for

CHOICE_SCHEMA = "bean.lab026.strategy_choice.v1"
CANDIDATES = ("reflection", "skill", "prompt")
CONTROL_ARMS = ("cold", "placebo")


def choose_strategy(bank, trial, domain, minimum_gain=1):
    """Select a contextual learning mechanism based on judged, matched trials.

    The caller owns all labels. This function makes no new truth claims and
    cannot access hidden holdout answers or approve production deployment.
    """
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("Domain required")
    if type(minimum_gain) is not int or not 1 <= minimum_gain <= 1000:
        raise ValueError("minimum_gain must be positive")
    if trial.get("schema") != SCHEMA or not trial.get("receipt_hash"):
        raise ValueError("Expected a genuine Lab026 experiment receipt")
    if trial.get("provider_kind") not in ("synthetic_fixture", "real_model", "observed_outcomes"):
        raise ValueError("Trial provider classification missing")
    # Never choose from a fabricated or edited caller-supplied scorecard:
    # reconcile all values with the append-only BEAN journal entry.
    saved = [
        row["data"] for row in bank.journal.events()
        if row.get("kind") == "trial"
        and row["data"].get("receipt_hash") == trial["receipt_hash"]
    ]
    presented = {k: v for k, v in trial.items() if k != "journal_tip"}
    if len(saved) != 1 or saved[0] != presented:
        raise ValueError("Selection receipt must match BEAN's recorded trial")

    required = (*CONTROL_ARMS, *CANDIDATES)
    if set(trial.get("arms", ())) != set(required):
        raise ValueError("Compare cold, irrelevant placebo and every candidate")
    if not material_for(bank, "placebo", domain).strip():
        raise ValueError("Independent unrelated-domain placebo lesson required")
    for arm in CANDIDATES:
        if not material_for(bank, arm, domain).strip():
            raise ValueError("Missing development lesson for " + arm)

    n = trial.get("cases", 0) * trial.get("replicates", 0)
    if not isinstance(n, int) or n < 1:
        raise ValueError("Invalid trial sample size")
    rows = trial.get("records", [])
    if not isinstance(rows, list) or len(rows) != n * len(required):
        raise ValueError("Incomplete paired trial")
    scores = {}
    for arm in required:
        group = [row for row in rows if row.get("arm") == arm]
        if len(group) != n or any(type(row.get("passed")) is not bool for row in group):
            raise ValueError("Missing or non-Boolean judgments for arm " + arm)
        scores[arm] = sum(row["passed"] for row in group)
        if trial.get("scores", {}).get(arm) != scores[arm]:
            raise ValueError("Receipt scores disagree with individual verdicts")
    # All arms must have the same (task_id, replicate) evaluation opportunities.
    identifiers = [
        {(r.get("task_id"), r.get("replicate")) for r in rows
         if r.get("arm") == arm}
        for arm in required
    ]
    if len(identifiers[0]) != n or any(keys != identifiers[0] for keys in identifiers):
        raise ValueError("Unequal paired evaluation samples")

    improvements = [
        arm for arm in CANDIDATES
        if scores[arm] >= scores["cold"] + minimum_gain
        and scores[arm] > scores["placebo"]
    ]
    # Stable tie order prevents nondeterministic selection across restarts.
    winner = sorted(improvements, key=lambda arm: (-scores[arm], CANDIDATES.index(arm)))[0] \
        if improvements else "cold"
    result = {
        "schema": CHOICE_SCHEMA,
        "domain": domain,
        "arm": winner,
        "scores": scores,
        "cases": trial["cases"],
        "replicates": trial["replicates"],
        "provider_kind": trial["provider_kind"],
        "model_id": trial["model_id"],
        "source_trial_hash": trial["receipt_hash"],
        "control_improvement_observed": winner != "cold",
        "scope": "selection_trial_only_not_holdout",
        "model_weights_modified": False,
        "independent_learning_proof": False,
    }
    result["journal_tip"] = bank.record_selection(result)
    return result
