"""Verify real reward callback accounting in BEAN's synthetic learner.

This checks measured calls, not just a self-reported counter. It is a
synthetic unit regression, not a restored-Core learning simulation.
"""
from __future__ import annotations

import pytest

from bean.evaluation.active_abstraction_benchmark import World
from bean.learning.active_hypothesis import ACTIONS, discover


@pytest.mark.parametrize("budget", (3, 6, 12))
@pytest.mark.parametrize("method", ("disagreement", "passive"))
@pytest.mark.parametrize("force_abstain", (False, True))
def test_validation_reward_calls_match_actual_callback(budget, method, force_abstain):
    world = World(20261114, "difference")
    train = tuple(str(100 + i) for i in range(40))
    validation = tuple(str(1000 + i) for i in range(8))
    calls = []

    def measured_reward(case, action):
        calls.append((case, action))
        return world.feedback(case, action)

    report = discover(
        probe_ids=train,
        validation_probe_ids=validation,
        observe=world.observe,
        reward=measured_reward,
        budget=budget,
        method=method,
        seed=14,
        include_products=True,
        min_gap=1000 if force_abstain else 0.08,
    )

    training_calls = [item for item in calls if item[0] in train]
    validation_calls = [item for item in calls if item[0] in validation]
    assert len(training_calls) == len(ACTIONS) * budget
    assert len(validation_calls) == len(ACTIONS) * len(validation)
    assert len(calls) == report["reward_calls"]
    assert len(calls) == len(ACTIONS) * (budget + len(validation))
    assert set(case for case, _ in training_calls) == {
        row["probe_id"] for row in report["records"]
    }
    for case in validation:
        assert sorted(action for pid, action in validation_calls if pid == case) == list(ACTIONS)
    if force_abstain:
        assert report["selected_rule"] is None
        assert report["status"] == "abstain"
    assert report["validation"]["used_for_candidate_generation"] is False
    assert report["blind_cases_used"] is False
