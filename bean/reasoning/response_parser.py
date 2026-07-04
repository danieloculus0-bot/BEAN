"""Parse structured output for Brain 0.11."""

import json

DEFAULT_RESPONSE = {"summary": "No structured response parsed.", "observations": [], "interpretations": [], "assumptions": [], "uncertainties": [], "evidence_refs": [], "candidate_steps": [], "risk_flags": [], "referenced_hypothesis_ids": [], "confidence": 0.0}


def parse_response(raw_text: str) -> dict:
    try:
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict):
            out = dict(DEFAULT_RESPONSE)
            out["parse_success"] = False
            return out
        out = dict(DEFAULT_RESPONSE)
        out.update(parsed)
        out["parse_success"] = True
        out["confidence"] = max(0.0, min(1.0, float(out.get("confidence", 0.5))))
        return out
    except Exception as exc:
        out = dict(DEFAULT_RESPONSE)
        out.update({"parse_success": False, "parse_error": str(exc), "raw_text": raw_text})
        return out
