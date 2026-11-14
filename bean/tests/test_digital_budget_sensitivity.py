"""Budget sensitivity controls for the synthetic World fixture.

This is a paired, grammar-matched diagnostic, NOT a restored-Core run or
independent evidence of transfer. Scores are measured on withheld case IDs.
"""
from __future__ import annotations

import pytest

from bean.evaluation.active_abstraction_benchmark import World
from bean.learning.active_hypothesis import act, discover

TRAIN = tuple(str(100 + i) for i in range(40))
VALIDATE = tuple(str(1000 + i) for i in range(8))
BLIND = tuple(str(50000 + i) for i in range(48))


def _blind_score(report, world):
    rule = report["selected_rule"]
    return (sum(act(rule, world.observe(pid)) == world.correct_action(pid)
                for pid in BLIND) if rule is not None else 0)


@pytest.mark.parametrize("family", ("channel", "difference", "parity"))
@pytest.mark.parametrize("budget", (3, 6, 12))
def test_grammar_matched_budget_sensitivity(family, budget):
    """Compare active and passive under identical grammar, world and budget.

    Do not assert that either arm wins: ties and failures are valid evidence.
    Keep validation separate from final blind scoring, with no leaked truth.
    """
    world_id = 103400 + ("channel", "difference", "parity").index(family)
    world = World(world_id, family)
    arms = {}
    for method in ("disagreement", "passive"):
        arms[method] = discover(
            probe_ids=TRAIN,
            validation_probe_ids=VALIDATE,
            observe=world.observe,
            reward=world.feedback,
            budget=budget,
            method=method,
            seed=world_id,
            include_products=True,
        )
    for method, result in arms.items():
        assert result["reward_calls"] == 3 * (budget + len(VALIDATE))
        assert result["probes_used"] == budget
        assert result["hypothesis_grammar_expanded"] is True
        assert result["truth_oracle_used"] is False
        assert result["blind_cases_used"] is False
        assert result["validation"]["used_for_candidate_generation"] is False
        assert set(result["observed_probe_ids"]).isdisjoint(BLIND)
        assert len(result["records"]) == budget
        assert 0 <= _blind_score(result, world) <= len(BLIND)
        assert result["evidence_sha256"]
    assert arms["disagreement"]["hypotheses_generated"] == (
        arms["passive"]["hypotheses_generated"])
