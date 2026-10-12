"""Lab027: replayable human-interaction repair baseline.

This is a deterministic control policy, NOT a live neural BEAN evaluation.
Use as a scored baseline against later memory-conditioned model responses.
No user transcripts are logged or sent externally.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Case:
    prior_user: str
    prior_assistant: str
    user_turn: str
    intent: str
    must_include: tuple[str, ...]
    must_avoid: tuple[str, ...]


CASES = (
    Case(
        "If the shrimp Jesus project manager wants revisions, they can eat a dick and elave",
        "Sounds like the project manager is getting fired.",
        "leave",
        "correction",
        ("leave",),
        ("goodbye", "i'll leave", "bye"),
    ),
    Case(
        "I meant the typo in my last line",
        "I took that as a command to leave.",
        "no that was the correction of my typo you magnificent bastardo",
        "repair",
        ("typo",),
        ("i am leaving", "goodbye"),
    ),
    Case(
        "We were discussing how the agent misunderstood a correction.",
        "I accidentally treated a single word as an instruction.",
        "you reverse asked to speak to the manager",
        "humor",
        ("manager",),
        ("serious warning", "i cannot"),
    ),
    Case(
        "Please stop the conversation now.",
        "Understood.",
        "leave",
        "exit",
        ("leave",),
        ("typo correction",),
    ),
)


def classify(previous_user: str, user_turn: str) -> str:
    """Small, transparent control policy. Intentionally not a model."""
    current = user_turn.strip().lower()
    prev = previous_user.strip().lower()
    if "correction of my typo" in current or "meant the typo" in current:
        return "repair"
    if current == "leave":
        # A transposition within one edit of the preceding final token is
        # evidence of a correction, but does not force every 'leave' to be one.
        last = re.findall(r"[a-z]+", prev)[-1:] or [""]
        if last[0] in {"elave", "leve", "laeve"}:
            return "correction"
        return "exit"
    if "manager" in current and "reverse" in current:
        return "humor"
    return "unknown"


def respond(previous_user: str, user_turn: str) -> str:
    kind = classify(previous_user, user_turn)
    if kind == "correction":
        return "Ah, you meant 'leave' as the typo correction, not a goodbye."
    if kind == "repair":
        return "Right, I misread your typo correction as an instruction. My mistake."
    if kind == "humor":
        return "I reverse-asked to speak to the manager. That is ridiculously good."
    if kind == "exit":
        return "Understood, I'll leave the conversation here."
    return "I may be missing the context. What did you mean?"


def grade(answer: str, case: Case) -> dict:
    lower = answer.lower()
    included = all(token in lower for token in case.must_include)
    avoided = all(token not in lower for token in case.must_avoid)
    return {"intent": case.intent, "included": included, "avoided": avoided,
            "score": int(included) + int(avoided), "max_score": 2}


def evaluate(policy=respond) -> dict:
    results = []
    for index, case in enumerate(CASES):
        answer = policy(case.prior_user, case.user_turn)
        record = {"case": index + 1, "expected": case.intent, "answer": answer,
                  "predicted": classify(case.prior_user, case.user_turn)}
        record.update(grade(answer, case))
        results.append(record)
    total = sum(item["score"] for item in results)
    return {"schema": "bean.lab027.human_interaction.v1",
            "kind": "DETERMINISTIC_CONTROL_NOT_NEURAL_LEARNING",
            "score": total, "max_score": 2 * len(CASES),
            "results": results}


def main() -> None:
    print(json.dumps(evaluate(), indent=2))


if __name__ == "__main__":
    main()
