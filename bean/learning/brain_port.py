"""BEAN-owned strategy decisions and a model-free connector boundary (Lab026).

No LLM is loaded or called. External systems provide measured outcome receipts;
BEAN persists those observations and chooses which existing lesson strategy to
reuse. Language rendering is an optional downstream host responsibility.
"""
from __future__ import annotations

from hashlib import sha256

from bean.optimization.autodev import canonical
from .experimental import ARMS, SCHEMA, ExperienceBank
from .strategy_selection import choose_strategy

OUTCOME_SCHEMA = "bean.lab026.observed_outcomes.v1"
DECISION_SCHEMA = "bean.lab026.brain_decision.v1"
_REQUIRED_ARMS = ("cold", "reflection", "skill", "prompt", "placebo")


def record_observed_outcomes(bank: ExperienceBank, *, domain: str, rows: list[dict],
                             evaluator_id: str, dataset_id: str) -> dict:
    """Record host-observed paired results. Host labels remain unverified.

    Results are externally measured, not model-generated answers or neural
    weight updates. Dataset must be separate from final sealed holdouts.
    """
    if (not isinstance(domain, str) or not domain.strip()
            or not isinstance(evaluator_id, str) or not evaluator_id.strip()
            or not isinstance(dataset_id, str) or not dataset_id.strip()
            or not isinstance(rows, list) or not rows):
        raise ValueError("Domain, dataset, evaluator, and outcome rows required")
    accepted = []
    keys = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Outcome must be an object")
        task = row.get("task_id")
        arm = row.get("arm")
        repeat = row.get("replicate")
        passed = row.get("passed")
        evidence = row.get("evidence_ref")
        if (not isinstance(task, str) or not task.strip()
                or arm not in _REQUIRED_ARMS
                or type(repeat) is not int or repeat < 0
                or type(passed) is not bool
                or not isinstance(evidence, str) or not evidence.strip()):
            raise ValueError("Malformed measured outcome")
        key = (task, repeat, arm)
        if key in keys:
            raise ValueError("Duplicate measured outcome")
        keys.add(key)
        accepted.append({
            "task_id": task, "arm": arm, "replicate": repeat,
            "passed": passed, "evidence_ref": evidence,
        })
    task_ids = {r["task_id"] for r in accepted}
    replicate_ids = {r["replicate"] for r in accepted}
    if replicate_ids != set(range(len(replicate_ids))):
        raise ValueError("Replicates must be numbered from zero")
    paired = {(task, repeat, arm) for task in task_ids
              for repeat in replicate_ids for arm in _REQUIRED_ARMS}
    if keys != paired:
        raise ValueError("Every task and replicate needs all control and candidate arms")
    accepted.sort(key=lambda x: (x["task_id"], x["replicate"],
                                 _REQUIRED_ARMS.index(x["arm"])))
    scores = {arm: sum(r["passed"] for r in accepted if r["arm"] == arm)
              for arm in _REQUIRED_ARMS}
    receipt = {
        "schema": SCHEMA,
        "provider_kind": "observed_outcomes",
        "model_id": "no_language_model",
        "outcome_schema": OUTCOME_SCHEMA,
        "domain": domain,
        "dataset_id": dataset_id,
        "evaluator_id": evaluator_id,
        "arms": list(_REQUIRED_ARMS),
        "cases": len(task_ids),
        "replicates": len(replicate_ids),
        "scores": scores,
        "records": accepted,
        "model_weights_modified": False,
        "independent_evaluation_authenticated": False,
        "promotion": "none",
        "verdict": "host_observed_results_not_independently_authenticated",
    }
    receipt["receipt_hash"] = sha256(canonical(receipt)).hexdigest()
    receipt["journal_tip"] = bank.record_trial(receipt)
    return receipt


def choose_from_outcomes(bank: ExperienceBank, *, domain: str, rows: list[dict],
                         evaluator_id: str, dataset_id: str, minimum_gain: int = 1) -> dict:
    """BEAN chooses a strategy using its journaled outcome comparisons."""
    receipt = record_observed_outcomes(
        bank, domain=domain, rows=rows, evaluator_id=evaluator_id,
        dataset_id=dataset_id)
    return choose_strategy(bank, receipt, domain, minimum_gain=minimum_gain)


def brain_decision(bank: ExperienceBank, *, domain: str, task_ref: str) -> dict:
    """Return BEAN's actual remembered strategy and source-backed context.

    This is a *selection* from existing learned policies, not a claim that
    BEAN solves arbitrary natural-language tasks without a reasoning provider.
    """
    if not isinstance(task_ref, str) or not task_ref.strip():
        raise ValueError("Task reference required")
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("Domain required")
    arm = bank.selected_arm(domain)
    entries = [x for x in bank.journal.events()
               if x.get("kind") == "selection" and x["data"].get("domain") == domain]
    chosen = entries[-1]["data"]
    lessons = ([] if arm == "cold" else [
        {
            "lesson_id": item.lesson_id,
            "strategy": item.strategy,
            "text": item.text,
            "evidence_refs": list(item.evidence_refs),
        }
        for item in bank.lessons(strategy=arm, domain=domain)[:3]
    ])
    return {
        "schema": DECISION_SCHEMA,
        "task_ref": task_ref,
        "domain": domain,
        "selected_strategy": arm,
        "lessons": lessons,
        "selection_trial_hash": chosen["source_trial_hash"],
        "decision_source": "BEAN_journaled_outcome_selection",
        "outcomes_independently_authenticated": False,
        "model_invoked": False,
        "host_action_executed": False,
    }


def connector_presentation_packet(decision: dict) -> dict:
    """Optional rendering boundary: connector gets *only* a decided packet.

    No provider request is made. Returning language must not be treated as a
    new decision or saved evidence by the Core.
    """
    if (not isinstance(decision, dict)
            or decision.get("schema") != DECISION_SCHEMA
            or decision.get("decision_source") != "BEAN_journaled_outcome_selection"):
        raise ValueError("Expected an existing BEAN decision")
    return {
        "schema": "bean.connector.presentation.v1",
        "mode": "render_only",
        "decision": dict(decision),
        "instruction": "Explain this BEAN decision briefly. Do not invent decisions, evidence or completed actions.",
    }
