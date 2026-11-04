"""Cluster-aware analysis of frozen paired transfer evaluations.

Research-only: family labels are declared by experimenters, not authenticated.
A positive aggregate does not establish independent transfer or AGI.
"""
from collections import defaultdict
from .preregistration import audit_preregistration


def family_paired_score(plan, anchor_digest, outcomes):
    """Count a family once, not once per correlated case.

    A family is a win only when candidate is never worse on any member
    and is better on at least one. A family is a loss if any member
    regresses, even if other members improve. This conservative rule
    prevents a large correlated family from drowning out failures.
    """
    audit = audit_preregistration(plan, anchor_digest, outcomes)
    if not audit["valid"]:
        return {"valid": False, "reason": audit["reason"],
                "family_net_gain": None, "case_audit": audit}
    families = defaultdict(list)
    by_id = {c["case_id"]: c for c in plan["cases"]
             if c["split"] in ("heldout", "ood")}
    for outcome in outcomes:
        families[by_id[outcome["case_id"]]["family_id"]].append(outcome)
    wins = losses = ties = 0
    for family in sorted(families):
        rows = families[family]
        has_loss = any(r["baseline"] and not r["candidate"] for r in rows)
        has_win = any(r["candidate"] and not r["baseline"] for r in rows)
        if has_loss:
            losses += 1
        elif has_win:
            wins += 1
        else:
            ties += 1
    return {"valid": True, "family_wins": wins, "family_losses": losses,
            "family_ties": ties, "family_count": len(families),
            "family_net_gain": wins - losses,
            "case_audit": audit,
            "claim": "conservative_family_clustered_descriptive_only"}
