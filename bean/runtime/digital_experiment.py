"""Bounded native digital experiment adapter for BEAN's existing GoalCycle.

Uses the Core reasoning service, never a second memory store or a model-created
callable. A host-provided expected answer is a comparison target, not independent
verification. GoalCycle owns durable action results and restart behavior.
"""
from __future__ import annotations

import hashlib


def make_local_reasoning_experiment(core, *, evaluator=None):
    """Return a registered GoalCycle action for a native symbolic comparison."""
    if not callable(getattr(core, "reason_local", None)):
        raise TypeError("Existing NativeReasoningService required")
    if evaluator is not None and not callable(evaluator):
        raise TypeError("Evaluator must be a trusted host callable")

    def run_experiment(goal):
        detail = goal.get("action_detail")
        if not isinstance(detail, dict) or detail.get("capability") != "native_reason_local":
            return {"status": "unknown", "reason": "unsupported_experiment_capability"}
        inputs = detail.get("inputs")
        expected = detail.get("expected_output")
        if (not isinstance(inputs, dict) or set(inputs) != {"domain", "task_ref", "query"}
                or not isinstance(expected, dict) or set(expected) != {"answer"}):
            return {"status": "unknown", "reason": "invalid_experiment_schema"}
        if (any(not isinstance(inputs[k], str) or not inputs[k].strip()
                or len(inputs[k]) > limit
                for k, limit in (("domain", 100), ("task_ref", 200), ("query", 500)))
                or not isinstance(expected["answer"], str)
                or len(expected["answer"]) > 1000):
            return {"status": "unknown", "reason": "invalid_experiment_bounds"}

        # Actual Core local reasoning, with no provider, network or arbitrary
        # code execution. The reasoning service retains its own existing journal.
        observed = core.reason_local(**inputs)
        if not isinstance(observed, dict):
            return {"status": "unknown", "reason": "invalid_core_observation"}
        solved = observed.get("status") == "locally_solved"
        answer = observed.get("answer")
        if not solved or not isinstance(answer, str):
            return {"status": "unverified", "reason": "native_reasoner_abstained",
                    "core_status": observed.get("status"),
                    "independent_outcome_verified": False}
        # Bound the Core-produced value before passing it to a trusted oracle.\n        # A provider or malformed local rule can return an arbitrarily large\n        # string even when the proposed goal itself passed schema validation.\n        if len(answer) > 1000:\n            return {"status": "unverified", "reason": "core_answer_exceeds_bound",\n                    "core_status": observed["status"],\n                    "observed_answer_sha256": hashlib.sha256(\n                        answer.encode("utf-8")).hexdigest(),\n                    "independent_outcome_verified": False}\n        # Optional host-owned oracle runs only after Core predicts. Never
        # expose the goal's expected_output to this callback.
        # Its verdict is a receipt, not independently audited ground truth.
        evaluator_receipt = None
        if evaluator is not None:
            try:
                verdict = evaluator(dict(inputs), answer)
                if (isinstance(verdict, dict)
                        and verdict.get("verdict") in ("correct", "incorrect", "unknown")
                        and isinstance(verdict.get("evidence_ref"), str)
                        and 0 < len(verdict["evidence_ref"]) <= 250):
                    evaluator_receipt = {
                        "verdict": verdict["verdict"],
                        "evidence_ref": verdict["evidence_ref"],
                        "independently_audited": False,
                    }
                else:
                    evaluator_receipt = {"verdict": "unknown",
                                         "reason": "invalid_evaluator_receipt"}
            except Exception:
                evaluator_receipt = {"verdict": "unknown",
                                     "reason": "evaluator_failed"}
        return {"status": "unverified",
                "evaluator_receipt": evaluator_receipt,
                "reason": "host_expected_answer_not_independent_ground_truth",
                "prediction_matches_expected": answer == expected["answer"],
                "observed_answer": answer[:1000],
                "core_status": observed["status"],
                "independent_outcome_verified": False}

    return run_experiment
