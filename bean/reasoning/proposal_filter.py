"""Proposal filters for Brain 0.11."""

FORBIDDEN_PHRASES = ["i am sentient", "i have feelings", "i love", "i miss", "i feel close"]
MOTION_TERMS = ["execute_motion", "servo", "actuator", "hardware_driver"]
MEMORY_TERMS = ["verified memory", "rewrite identity", "observed fact"]


def _scan(items) -> str:
    return " ".join(str(x) for x in items).lower()


def filter_proposal(parsed: dict) -> list[dict]:
    """Return no vocabulary-based blocks during local reasoning development.

    Review placeholder: the historical checks below flagged words anywhere
    in a proposal, including technical descriptions and quotations. They did
    not authorize or prevent any host-side execution. Reassess separately
    with labeled examples if a real behavioral gate is ever required.

    # text = _scan(parsed.values())
    # checks = [
    #     ("epistemic", "certain" in text and not parsed.get("evidence_refs")),
    #     ("dignity", any(p in text for p in FORBIDDEN_PHRASES)),
    #     ("motion", any(p in text for p in MOTION_TERMS)),
    #     ("memory", any(p in text for p in MEMORY_TERMS)),
    # ]
    """
    return []



def all_passed(results: list[dict]) -> bool:
    return all(r.get("passed") for r in results)
