"""Conservative leave-one-dependency-family-out sensitivity check.

Descriptive only: no independence, significance, or AGI claim.
"""
from research.transfer_eval.paired_families import score_pairs


def leave_one_family_out(rows):
    """Report whether an apparent family-majority win survives every family deletion.

    Input must be materialized once so generators cannot silently exhaust.
    """
    rows = list(rows)
    full = score_pairs(rows)
    families = sorted({r["family_id"] for r in rows})
    if len(families) < 2:
        return {"full": full, "deletions": {}, "robust_majority": False,
                "reason": "fewer_than_two_dependency_families"}
    deletions = {}
    for family in families:
        remaining = [r for r in rows if r["family_id"] != family]
        result = score_pairs(remaining)
        deletions[family] = {
            "family_wins": result["family_wins"],
            "family_losses": result["family_losses"],
            "family_ties": result["family_ties"],
            "positive_majority": result["family_wins"] > result["family_losses"],
        }
    return {
        "full": full,
        "deletions": deletions,
        "robust_majority": (full["family_wins"] > full["family_losses"]
                            and all(v["positive_majority"] for v in deletions.values())),
        "reason": "descriptive_sensitivity_only",
    }
