"""BEAN-owned batched inference evaluation with per-task immutable evidence.

Batch within an arm, NEVER across cold and learned-memory arms. This reduces
provider calls while retaining the same BEAN selector and per-task scoring.
The external model is an interchangeable inference backend: it does not own
BEAN's lessons, choices, feedback, hash journal or holdout labels.
"""
from __future__ import annotations

from hashlib import sha256
from .experimental import (
    ARMS, SCHEMA, canonical, material_for, question_fingerprint,
)


def run_batched_paired_trial(*, bank, cases, model, judge, arms=ARMS,
                             context_chars=800, task_aware=True):
    """One call per arm, many independent public questions per provider call.

    Responses and context digests are recorded individually, even when their
    source is the same model request. Control arms never share an input call.
    """
    cases = list(cases)
    arms = tuple(arms)
    if (not cases or type(task_aware) is not bool or not task_aware
            or not 40 <= context_chars <= 12000
            or len(set(arms)) != len(arms)
            or any(a not in (*ARMS, "adaptive") for a in arms)
            or not callable(getattr(model, "complete_batch", None))
            or model.provider_kind not in ("synthetic_fixture", "real_model")
            or not isinstance(model.model_id, str) or not model.model_id):
        raise ValueError("Invalid task-aware batched evaluation")
    if len({c.task_id for c in cases}) != len(cases):
        raise ValueError("Duplicate task identities")
    identities = [question_fingerprint(c.public_question) for c in cases]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate normalized public questions")

    records = []
    for arm in arms:
        payload = []
        for case in cases:
            ctx = material_for(
                bank, arm, case.domain, query=case.public_question)
            payload.append({
                "task_id": case.task_id,
                "question": case.public_question,
                "context": ctx[:context_chars],
            })
        # Deliberate isolation: model sees *only* one arm per request.
        replies = model.complete_batch(payload)
        if (not isinstance(replies, dict)
                or set(replies) != {c.task_id for c in cases}
                or any(not isinstance(replies[c.task_id], str) for c in cases)):
            raise ValueError("Provider batch omitted or duplicated task identities")
        for index, (case, prompt) in enumerate(zip(cases, payload)):
            answer = replies[case.task_id]
            passed = judge(case.expected, answer)
            if type(passed) is not bool:
                raise TypeError("Judge must return a Boolean verdict")
            records.append({
                "task_id": case.task_id, "arm": arm, "replicate": 0,
                "question_sha256": identities[index],
                "context_sha256": sha256(prompt["context"].encode()).hexdigest(),
                "answer_sha256": sha256(answer.encode()).hexdigest(),
                "passed": passed,
            })
    scores = {arm: sum(row["passed"] for row in records if row["arm"] == arm)
              for arm in arms}
    receipt = {
        "schema": SCHEMA,
        "provider_kind": model.provider_kind,
        "model_id": model.model_id,
        "arms": list(arms),
        "cases": len(cases),
        "replicates": 1,
        "context_chars": context_chars,
        "scores": scores,
        "question_fingerprint": "NFKC_casefold_whitespace_sha256_v1",
        "context_policy": "same_task_lexical_retrieval_as_decide_v1",
        "batching_policy": "one_isolated_request_per_arm_v1",
        "provider_requests": len(arms),
        "records": records,
        "model_weights_modified": False,
        "independent_evaluation_authenticated": False,
        "promotion": "none",
        "verdict": ("synthetic_fixture_not_learning_proof"
                    if model.provider_kind == "synthetic_fixture"
                    else "needs_external_blind_replication"),
    }
    receipt["receipt_hash"] = sha256(canonical(receipt)).hexdigest()
    receipt["journal_tip"] = bank.record_trial(receipt)
    return receipt
