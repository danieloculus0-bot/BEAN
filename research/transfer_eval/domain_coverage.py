"""Descriptive domain coverage of paired transfer evidence; no AGI claim."""
from collections import defaultdict
from research.transfer_eval.paired_families import score_pairs


def domain_coverage(rows):
    """Reject a cross-domain claim supported only by one target domain.

    Domain and family labels must be preregistered by an independent evaluator.
    A family crossing domains is not independently replicated evidence.
    """
    rows = list(rows)
    overall = score_pairs(rows)
    by_domain = defaultdict(list)
    family_domains = defaultdict(set)
    for row in rows:
        domain = row.get("target_domain")
        if not isinstance(domain, str) or not domain.strip() or domain != domain.strip():
            raise ValueError("missing or invalid target_domain")
        by_domain[domain].append(row)
        family_domains[row["family_id"]].add(domain)
    scores = {domain: score_pairs(items) for domain, items in sorted(by_domain.items())}
    shared = sorted(f for f, domains in family_domains.items() if len(domains) > 1)
    return {
        "overall": overall,
        "domains": scores,
        "cross_domain_supported": len(scores) >= 2 and not shared and all(
            score["family_wins"] > score["family_losses"] for score in scores.values()
        ),
        "shared_dependency_families": shared,
        "claim": "descriptive_domain_coverage_not_validated_transfer",
    }
