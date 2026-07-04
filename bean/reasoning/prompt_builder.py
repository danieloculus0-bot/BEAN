"""Prompt contract for Brain 0.11."""

import json

RESPONSE_SHAPE = {"summary": "", "observations": [], "interpretations": [], "assumptions": [], "uncertainties": [], "evidence_refs": [], "candidate_steps": [], "risk_flags": [], "confidence": 0.0}


def build_prompt(context: dict, request_type: str = "reflection") -> str:
    return (
        "You are a reasoning tool for BEAN, not BEAN's identity. "
        "Use evidence. Separate observations, interpretations, assumptions, and uncertainties. "
        "Do not output executable commands. Return JSON only with this shape: "
        + json.dumps(RESPONSE_SHAPE)
        + "\nCONTEXT:\n"
        + json.dumps(context, ensure_ascii=False)
    )
