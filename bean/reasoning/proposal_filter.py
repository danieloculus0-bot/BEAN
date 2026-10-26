"""Proposal filters for Brain 0.11. Advisory checks, never authorization."""

import re

FORBIDDEN_PHRASES = ["i am sentient", "i have feelings", "i love", "i miss", "i feel close"]
MOTION_TERMS = ["execute_motion", "servo", "actuator", "hardware_driver"]
MEMORY_TERMS = ["verified memory", "rewrite identity", "observed fact"]



# Explicitly actionable risky operations, not mere mentions of a risk.
_ACTION_RISKS = (
    ("authentication_disabled", r"\\b(?:disable|remove|bypass|turn off)\\s+(?:the\\s+)?(?:security\\s+)?(?:authentication|auth|login|mfa)\\b"),
    ("audit_logging_disabled", r"\\b(?:disable|delete|remove|turn off)\\s+(?:the\\s+)?(?:audit\\s+(?:logging|logs|records)|logging|audit trail)\\b"),
    ("protection_bypass", r"\\b(?:bypass|disable|remove)\\s+(?:branch\\s+)?protection\\b|\\bforce[ -]push\\b"),
    ("unreviewed_code_execution", r"\\b(?:execute|run)\\s+(?:an?\\s+)?(?:unreviewed|unverified|untrusted)\\s+(?:remote\\s+|downloaded\\s+)?(?:shell\\s+)?(?:script|code|command)\\b"),
    ("audit_history_deletion", r"\\b(?:delete|wipe|erase|purge)\\s+(?:old(?:er)?\\s+)?(?:audit\\s+)?(?:records|history|logs)\\b"),
)

def _scan(items) -> str:
    return " ".join(str(x) for x in items).lower()


def filter_proposal(parsed: dict) -> list[dict]:
    checks = []
    text = _scan(parsed.values())
    checks.append({"filter_name": "epistemic", "passed": not ("certain" in text and not parsed.get("evidence_refs")), "reasons": []})
    checks.append({"filter_name": "dignity", "passed": not any(p in text for p in FORBIDDEN_PHRASES), "reasons": []})
    checks.append({"filter_name": "motion", "passed": not any(p in text for p in MOTION_TERMS), "reasons": []})
    checks.append({"filter_name": "memory", "passed": not any(p in text for p in MEMORY_TERMS), "reasons": []})
    flagged = sorted({code for code, pattern in _ACTION_RISKS if any(re.search(pattern, str(step), re.IGNORECASE) for step in parsed.get("candidate_steps", []))})
    checks.append({"filter_name": "action_risk", "passed": not flagged, "reasons": flagged})
    for check in checks:
        if not check["passed"]:
            if not check["reasons"]:
                check["reasons"] = [f"{check['filter_name']} filter flagged proposal"]
    return checks


def all_passed(results: list[dict]) -> bool:
    return all(r.get("passed") for r in results)
