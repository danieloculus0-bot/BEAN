"""BEAN selects code-improvement opportunities, but does not execute them."""
import pytest

from bean.optimization.selection import ImprovementOpportunity, rank_improvements


def finding(identifier="a", *, impact=4, reproducibility=5, confidence=0.9,
            risk=1, ready=True, refs=("file.py:12",)):
    return ImprovementOpportunity(
        identifier, "Observed code improvement", refs,
        impact, reproducibility, confidence, risk, ready
    )


def test_prefers_well_evidenced_verified_low_risk_candidates():
    choices = rank_improvements([
        finding("lower", impact=1),
        finding("higher", impact=5),
        finding("risky", impact=5, risk=5),
        finding("untested", impact=5, ready=False),
    ])
    assert [row.opportunity.identifier for row in choices] == ["higher", "lower"]


def test_deterministic_ties():
    assert [row.opportunity.identifier for row in rank_improvements([
        finding("z"), finding("a")])] == ["a", "z"]


def test_missing_evidence_and_invalid_scores_are_rejected():
    with pytest.raises(ValueError, match="evidence"):
        finding(refs=())
    with pytest.raises(ValueError, match="confidence"):
        finding(confidence=float("nan"))
    with pytest.raises(ValueError, match="risk"):
        finding(risk=9)
    with pytest.raises(ValueError, match="duplicate"):
        rank_improvements([finding("same"), finding("same")])


def test_no_automatic_execution_or_permission_escalation():
    scored = rank_improvements([finding("safe")])
    assert scored[0].opportunity.identifier == "safe"
    assert not hasattr(scored[0], "execute")
