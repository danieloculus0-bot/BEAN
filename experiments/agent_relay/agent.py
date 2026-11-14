"""Local preference reasoning and optional BEAN model adapter.

No personal profile is accepted by the transport. A human remains responsible
for deciding whether to alter a personal preference or initiate contact.
"""
from __future__ import annotations

import json

from .protocol import DETAILS, SIGNALS, TOPICS


def local_preference_review(*, requested_minimum: float, candidate_value: float,
                            flexible: bool) -> dict:
    """Private-only example: close mismatch asks rather than silently excludes.

    Caller MUST NOT transmit this returned object over the relay. This remains
    with the local user and includes no inference about a real person.
    """
    if any(type(v) not in (int, float) for v in (requested_minimum, candidate_value)):
        raise ValueError("numeric preference example required")
    delta = candidate_value - requested_minimum
    if delta >= 0:
        return {"decision": "eligible", "needs_user_decision": False, "gap": 0.0}
    if flexible:
        return {"decision": "ask_local", "needs_user_decision": True,
                "gap": abs(float(delta))}
    return {"decision": "declined", "needs_user_decision": False,
            "gap": abs(float(delta))}


def model_signal(provider, *, topic: str, public_detail: str) -> str:
    """Use BEAN's existing provider.complete interface; validate model output.

    Only coarse explicitly shared categories are supplied to the model. The
    existing local Ollama provider can be plugged in; no fake LLM is silently
    substituted for unavailable inference.
    """
    if topic not in TOPICS or public_detail not in DETAILS:
        raise ValueError("invalid coarse prompt")
    if not callable(getattr(provider, "complete", None)):
        raise TypeError("actual BEAN provider required")
    prompt = (
        "You are a private-first agent-to-agent compatibility research assistant. "
        "Respond ONLY with JSON of the exact form: "
        '{"signal":"interested"} or {"signal":"compatible"} or '
        '{"signal":"incompatible"} or {"signal":"unknown"}. '
        "These are provisional hypotheses, not personal judgements. "
        f"Public topic: {topic}; approved coarse detail: {public_detail}. "
        "No personal stories, identities or explanations."
    )
    result = provider.complete(prompt)
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError("BEAN model provider unavailable")
    try:
        value = json.loads(result["raw_text"])
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("model returned invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"signal"} or value["signal"] not in SIGNALS:
        raise ValueError("model output failed allowlist")
    return value["signal"]
