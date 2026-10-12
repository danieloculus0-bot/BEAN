"""Independent challenge of the *other* BEAN development branch.

A dedicated GitHub Actions job checks out the actual selector PR commit into
a separate folder and supplies BEAN_SELECTOR_MODULE. Do not silently import
the peer branch's own fixture/tests as the independent oracle.
"""
import importlib.util
import os
from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="module")
def selector():
    peer_path = os.environ.get("BEAN_SELECTOR_MODULE")
    if not peer_path:
        pytest.skip("selector is independently checked out by the Lab017 peer CI")
    path = Path(peer_path)
    assert path.is_file(), "peer checkout missing: refuse to claim cross-branch coverage"
    spec = importlib.util.spec_from_file_location("bean_peer_selector_pinned", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def finding(module, name, *, risk=1, ready=True, confidence=0.75,
            impact=3, reproduce=3, refs=("test:source:12",)):
    return module.ImprovementOpportunity(
        identifier=name, description="Observed seeded reliability regression",
        evidence_refs=refs, impact=impact, reproducibility=reproduce,
        confidence=confidence, risk=risk, validation_ready=ready,
    )


def test_adversarial_unverified_high_impact_is_not_selected(selector):
    high = finding(selector, "seems-amazing", impact=5, ready=False, confidence=1)
    verified = finding(selector, "modest-reproducible", impact=2, reproduce=5)
    risky = finding(selector, "oversized-risk", impact=5, risk=5)
    ranked = selector.rank_improvements([risky, high, verified])
    assert [row.opportunity.identifier for row in ranked] == ["modest-reproducible"]


def test_tie_and_reordering_are_deterministic(selector):
    rows = [finding(selector, "z"), finding(selector, "a"), finding(selector, "m")]
    left = selector.rank_improvements(rows)
    right = selector.rank_improvements(list(reversed(rows)))
    assert [(x.opportunity.identifier, x.score) for x in left] == [
        (x.opportunity.identifier, x.score) for x in right]
    assert [r.opportunity.identifier for r in left] == ["a", "m", "z"]


def test_invalid_confidence_cannot_create_inf_or_nan_winner(selector):
    for value in (float("nan"), float("inf"), -0.01, 1.01, True):
        with pytest.raises(ValueError, match="confidence"):
            finding(selector, "bad-confidence", confidence=value)


def test_evidence_is_mandatory_and_no_output_executes(selector):
    with pytest.raises(ValueError, match="evidence"):
        finding(selector, "untraceable", refs=())
    rows = selector.rank_improvements([finding(selector, "safe")])
    assert len(rows) == 1
    assert not any(hasattr(rows[0], x) for x in ("execute", "apply", "merge"))


def test_duplicate_candidate_identifier_is_fatal(selector):
    with pytest.raises(ValueError, match="duplicate"):
        selector.rank_improvements([finding(selector, "repeat"),
                                   finding(selector, "repeat")])


def test_zero_reproducibility_does_not_win_by_impact(selector):
    no_repro = finding(selector, "no-repro", reproduce=0, impact=5)
    low_repro = finding(selector, "repro", reproduce=1, impact=1)
    out = selector.rank_improvements([no_repro, low_repro])
    assert [row.opportunity.identifier for row in out] == ["repro"]


def test_non_numeric_risk_budget_is_refused(selector):
    for value in (-1, 6, 2.2, True):
        with pytest.raises(ValueError, match="risk budget"):
            selector.rank_improvements([], max_risk=value)
