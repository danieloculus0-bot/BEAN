"""Pure audit of frozen evaluation plans; not evidence of independent execution.

A preregistration hash must be anchored in an external immutable receipt before
outcomes are collected. This module cannot authenticate the anchor or timestamps.
"""
import hashlib
import json

PLAN_KEYS = ("baseline_sha", "candidate_sha", "cases", "seed", "budget")
CASE_KEYS = ("case_id", "family_id", "target_domain", "split")


def canonical_digest(plan):
    """Hash an unambiguous JSON representation of a frozen plan."""
    if not isinstance(plan, dict) or set(plan) != set(PLAN_KEYS):
        raise ValueError("invalid plan fields")
    if not all(isinstance(plan[k], str) and plan[k].strip() for k in ("baseline_sha", "candidate_sha")):
        raise ValueError("missing revisions")
    if plan["baseline_sha"].strip() == plan["candidate_sha"].strip():
        raise ValueError("identical baseline and candidate revisions")
    if type(plan["seed"]) is not int or plan["seed"] < 0:
        raise ValueError("invalid seed")
    if not isinstance(plan["budget"], dict) or not plan["budget"]:
        raise ValueError("missing budget")
    for key, value in plan["budget"].items():
        if not isinstance(key, str) or not key or type(value) is not int or value < 0:
            raise ValueError("invalid budget")
    cases = plan["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("missing cases")
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != set(CASE_KEYS):
            raise ValueError("invalid case")
        if any(not isinstance(case[k], str) or not case[k].strip()
               for k in CASE_KEYS):
            raise ValueError("invalid case label")
        if case["case_id"] in seen:
            raise ValueError("duplicate case")
        seen.add(case["case_id"])
        if case["split"] not in ("train", "heldout", "ood"):
            raise ValueError("invalid split")
    payload = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                         allow_nan=False).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def audit_preregistration(plan, anchor_digest, outcomes):
    """Reject changed plans, missing/extra outcomes, or non-heldout evaluations.

    Anchor provenance and chronological ordering require independent verification.
    """
    digest = canonical_digest(plan)
    if not isinstance(anchor_digest, str) or digest != anchor_digest:
        return {"valid": False, "reason": "plan_digest_mismatch", "digest": digest}
    expected = {c["case_id"] for c in plan["cases"] if c["split"] in ("heldout", "ood")}
    if not expected:
        return {"valid": False, "reason": "no_heldout_or_ood_cases",
                "digest": digest, "expected_cases": 0, "observed_cases": 0,
                "claim": "plan_integrity_only_anchor_timing_unverified"}
    observed = set()
    if not isinstance(outcomes, list):
        raise ValueError("outcomes must be a list")
    for outcome in outcomes:
        if not isinstance(outcome, dict) or set(outcome) != {"case_id", "baseline", "candidate"}:
            raise ValueError("invalid outcome")
        cid = outcome["case_id"]
        if not isinstance(cid, str) or cid in observed:
            raise ValueError("invalid or duplicate outcome")
        if any(type(outcome[k]) is not bool for k in ("baseline", "candidate")):
            raise ValueError("outcomes must be boolean")
        observed.add(cid)
    paired = [o for o in outcomes if o["case_id"] in expected]
    wins = sum(o["candidate"] and not o["baseline"] for o in paired)
    losses = sum(o["baseline"] and not o["candidate"] for o in paired)
    ties = len(paired) - wins - losses
    return {"paired_wins": wins, "paired_losses": losses, "paired_ties": ties,
            "paired_net_gain": (wins - losses) if observed == expected else None,
            "valid": observed == expected, "reason": (
        "complete_frozen_eval" if observed == expected else "missing_or_extra_cases"),
        "digest": digest, "expected_cases": len(expected), "observed_cases": len(observed),
        "claim": "plan_integrity_only_anchor_timing_unverified"}
