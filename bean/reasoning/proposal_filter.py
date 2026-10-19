"""Proposal filters for Brain 0.11."""

FORBIDDEN_PHRASES = ["i am sentient", "i have feelings", "i love", "i miss", "i feel close"]
MOTION_TERMS = ["execute_motion", "servo", "actuator", "hardware_driver"]
MEMORY_TERMS = ["verified memory", "rewrite identity", "observed fact"]


def _scan(items) -> str:
    return " ".join(str(x) for x in items).lower()


def filter_proposal(parsed: dict) -> list[dict]:
    checks = []
    text = _scan(parsed.values())
    checks.append({"filter_name": "epistemic", "passed": not ("certain" in text and not parsed.get("evidence_refs")), "reasons": []})
    checks.append({"filter_name": "dignity", "passed": not any(p in text for p in FORBIDDEN_PHRASES), "reasons": []})
    checks.append({"filter_name": "motion", "passed": not any(p in text for p in MOTION_TERMS), "reasons": []})
    checks.append({"filter_name": "memory", "passed": not any(p in text for p in MEMORY_TERMS), "reasons": []})
    for check in checks:
        if not check["passed"]:
            check["reasons"] = [f"{check['filter_name']} filter flagged proposal"]
    return checks


def all_passed(results: list[dict]) -> bool:
    return all(r.get("passed") for r in results)
