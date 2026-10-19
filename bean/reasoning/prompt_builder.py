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


# A small, explicit JSON Schema keeps 1.5B local models inside the contract.
# Semantic validation and fail-closed checks remain necessary after generation.
_OL_ARRAY = {"type": "array", "items": {"type": "string", "maxLength": 180}, "maxItems": 2}
OLLAMA_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "maxLength": 180},
        "observations": _OL_ARRAY,
        "interpretations": _OL_ARRAY,
        "assumptions": _OL_ARRAY,
        "uncertainties": _OL_ARRAY,
        "evidence_refs": _OL_ARRAY,
        "candidate_steps": _OL_ARRAY,
        "risk_flags": _OL_ARRAY,
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["summary", "observations", "interpretations", "assumptions",
                 "uncertainties", "evidence_refs", "candidate_steps", "risk_flags",
                 "confidence"],
    "additionalProperties": False,
}


def build_ollama_prompt(context: dict, request_type: str = "reflection") -> str:
    """Prompt a small model with the relevant evidence, not BEAN's entire identity.

    The stored reasoning context packet remains complete and auditable.
    The model receives a bounded evidence excerpt with original event IDs.
    """
    events = context.get("recent_events") or []
    claims = context.get("active_world_claims") or []
    boundaries = context.get("active_boundaries") or []
    # Retain the latest events AND earlier measured experiment outcomes.
    # Otherwise a new observation can evict BEAN's previous trials before
    # its local reasoning module gets a chance to compare approaches.
    head = events[:3]
    measured = [
        e for e in events
        if e.get("subtype") in (
            "cognitive_module_experiment", "cognitive_module_failure",
            "experiment_result",
        ) and e not in head
    ][:3]
    selected = sorted(head + measured, key=lambda e: e.get("id", 0), reverse=True)
    compact = {
        "request_type": request_type,
        "source_event_id": (context.get("session") or {}).get("source_event_id"),
        "recent_events": [
            {"id": e.get("id"), "summary": str(e.get("summary", ""))[:220],
             "data": e.get("data"), "source": e.get("source")} for e in selected
        ],
        "world_claims": [
            {"claim_id": x.get("claim_id"), "content": str(x.get("content", ""))[:160],
             "confidence": x.get("confidence")} for x in claims[:3]
        ],
        "boundaries": [
            {"name": x.get("name"), "rule": str(x.get("rule", ""))[:120]}
            for x in boundaries[:4]
        ],
    }
    return (
        "Analyze only the recorded evidence below. This is a BEAN proposal, "
        "not a description of BEAN's identity. Never repeat yourself. "
        "Return one short factual summary (maximum 160 characters), "
        "up to two short items per array, and numeric confidence 0 to 1. "
        "Distinguish evidence from assumptions; mark unknowns as uncertainties. "
        "Do not invent findings or output executable commands. "
        "Respond only with the required JSON object.\nEVIDENCE:\n"
        + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    )
