"""Prospective, dependency-aware paired transfer evaluation (stdlib only).

Input is independently labeled, synthetic/public evaluation outcomes. This does
not authenticate labels or measure BEAN unless real runs supply the rows.
"""
from collections import defaultdict


def score_pairs(rows):
    """Compare candidate and baseline on matched cases without pseudoreplication.

    Each row: case_id, family_id, baseline_correct, candidate_correct (booleans).
    Families are conservative dependence clusters, not independent samples.
    """
    seen = set()
    families = defaultdict(list)
    for row in rows:
        case = row["case_id"]
        family = row["family_id"]
        if not isinstance(case, str) or not case or case in seen:
            raise ValueError("duplicate or invalid case_id")
        if not isinstance(family, str) or not family:
            raise ValueError("invalid family_id")
        b, c = row["baseline_correct"], row["candidate_correct"]
        if type(b) is not bool or type(c) is not bool:
            raise ValueError("outcomes must be independently scored booleans")
        seen.add(case)
        families[family].append(int(c) - int(b))
    if not seen:
        raise ValueError("no paired cases")
    per_family = {k: sum(v) for k, v in sorted(families.items())}
    return {
        "paired_cases": len(seen),
        "dependency_families": len(families),
        "case_wins": sum(x > 0 for v in families.values() for x in v),
        "case_losses": sum(x < 0 for v in families.values() for x in v),
        "case_ties": sum(x == 0 for v in families.values() for x in v),
        "family_wins": sum(x > 0 for x in per_family.values()),
        "family_losses": sum(x < 0 for x in per_family.values()),
        "family_ties": sum(x == 0 for x in per_family.values()),
        "family_net": per_family,
        "claim": "descriptive_only_not_independent_transfer_proof",
    }
