"""Conservative evidence/counsel arbitration for BEAN's existing reasoning service.

Not a semantic truth detector or an authority oracle. The host supplies
source qualifications and evidence status; BEAN records those assertions,
prefers adequate established answers, and declines when support is missing.
"""
from __future__ import annotations

from hashlib import sha256
from bean.optimization.autodev import canonical

POLICY = "bean.judgment.v1"
KINDS = ("established", "expert", "self")
CONFIDENCE = ("low", "medium", "high")
STAKES = ("low", "normal", "high")


def _text(value, name, limit=3000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(name + " must be nonempty bounded text")
    return value.strip()


def _flag(data, key, default=False):
    value = data.get(key, default)
    if type(value) is not bool:
        raise ValueError(key + " must be a Boolean")
    return value


def choose_counsel(*, domain, task_ref, query, candidates, stakes="normal",
                   conflicting_evidence=False):
    """Prefer adequate supported work over needless reinvention.

    These are rules for a proposed choice, NOT verification of claimed
    confidence, source authenticity, qualification, or real-world correctness.
    Nothing is called or executed; outputs remain host-attested proposals.
    """
    domain = _text(domain, "domain", 100).casefold()
    task_ref = _text(task_ref, "task_ref", 200)
    query = _text(query, "query")
    if stakes not in STAKES:
        raise ValueError("Unknown decision stakes")
    if type(conflicting_evidence) is not bool:
        raise ValueError("conflicting_evidence must be Boolean")
    if not isinstance(candidates, list) or len(candidates) > 12:
        raise ValueError("Need a list of at most twelve candidate answers")
    normalized = []
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("Candidate must be a mapping")
        kind = item.get("kind")
        if kind not in KINDS:
            raise ValueError("Unknown knowledge source kind")
        confidence = item.get("confidence", "low")
        if confidence not in CONFIDENCE:
            raise ValueError("Unknown confidence category")
        refs = item.get("evidence_refs")
        if not isinstance(refs, (list, tuple)) or not 1 <= len(refs) <= 12:
            raise ValueError("Candidate needs 1..12 evidence references")
        cleaned = {
            "kind": kind,
            "answer": _text(item.get("answer"), "candidate answer"),
            "source_ref": _text(item.get("source_ref"), "source reference", 500),
            "evidence_refs": [_text(r, "evidence reference", 500) for r in refs],
            "confidence": confidence,
            "adequate": _flag(item, "adequate"),
            "in_scope": _flag(item, "in_scope"),
            "current": _flag(item, "current"),
            "source_checked": _flag(item, "source_checked"),
            "qualified": _flag(item, "qualified"),
            "corroborated": _flag(item, "corroborated"),
        }
        normalized.append(cleaned)

    # All flags reflect the host's statements, even "source_checked" and
    # "corroborated": BEAN has not authenticated any external expert.
    def suitable(item):
        if not (item["adequate"] and item["in_scope"] and item["current"]
                and item["source_checked"]
                and item["confidence"] in ("medium", "high")):
            return False
        if item["kind"] == "expert" and not item["qualified"]:
            return False
        if stakes == "high" and not item["corroborated"]:
            return False
        return True

    eligible = [item for item in normalized if suitable(item)]
    eligible.sort(key=lambda item: (
        -CONFIDENCE.index(item["confidence"]),
        KINDS.index(item["kind"]), item["source_ref"]))
    chosen = eligible[0] if eligible else None
    reasons = []
    if conflicting_evidence:
        chosen = None
        decision = "defer"
        reasons.append("host_reported_conflict")
    elif len(eligible) > 1 and (
            eligible[0]["confidence"] == eligible[1]["confidence"]
            and eligible[0]["kind"] == eligible[1]["kind"]
            and eligible[0]["answer"].strip().casefold()
                != eligible[1]["answer"].strip().casefold()):
        # Different wording is NOT semantic contradiction proof. It merely
        # triggers review rather than allowing arbitrary silent selection.
        chosen = None
        decision = "defer"
        reasons.append("potential_peer_disagreement")
    elif chosen is not None:
        decision = "adopt"
        reasons.append("adequate_supported_" + chosen["kind"])
        reasons.append("novelty_not_required")
    elif stakes == "high" or any(
            x["kind"] == "expert" and x["qualified"] for x in normalized):
        decision = "defer"
        reasons.append("reliable_answer_not_established")
    else:
        decision = "explore"
        reasons.append("insufficient_evidence_for_adoption")

    return {
        "schema": POLICY,
        "domain": domain, "task_ref": task_ref,
        "query_sha256": sha256(query.encode("utf-8")).hexdigest(),
        "decision": decision,
        "answer": chosen["answer"] if chosen else None,
        "source_kind": chosen["kind"] if chosen else None,
        "selected_source_ref": chosen["source_ref"] if chosen else None,
        "selected_evidence_refs": list(chosen["evidence_refs"]) if chosen else [],
        "considered_source_refs": [x["source_ref"] for x in normalized],
        "reasons": reasons,
        "next_step": ("use_existing_answer" if chosen else
                      "request_review_or_verification" if decision == "defer"
                      else "research_or_test_without_assuming_success"),
        "stakes": stakes,
        "source_metadata_origin": "host_attested_not_independently_authenticated",
        "external_truth_verified": False,
        "model_invoked": False,
        "proposed_action_only": True,
    }
