"""Paired synthetic rule-reversal diagnostic for retained-prior adaptation.

This is an exploratory, bounded negative-control experiment, not AGI evidence.
A previous rule is learned from feedback, then the same environment reverses
its action rewards. Both arms receive identical fresh observations and budget.
The withheld evaluation is scored only after both discovery calls finish.
"""
from __future__ import annotations

import json
import unittest

from bean.evaluation.active_abstraction_benchmark import World
from bean.learning.active_hypothesis import act, discover


def reversal_trial(world_id: int, budget: int) -> dict:
    world = World(world_id, "channel")
    prior = discover(
        probe_ids=[str(100 + i) for i in range(40)],
        observe=world.observe, reward=world.feedback,
        budget=12, seed=world_id,
    )["selected_rule"]
    if prior is None:
        return {"world": world_id, "budget": budget, "status": "no_prior"}

    train = [str(1000 + i) for i in range(40)]
    blind = [str(50000 + i) for i in range(48)]
    # Verify disjoint sensor states, not just distinct case identifiers.
    prior_ids = [str(100 + i) for i in range(40)]
    observed = [world.observe(case) for case in prior_ids + train + blind]
    assert len(set(observed)) == len(observed), "Prior/train/blind state collision"
    seen = {"cold": [], "warm": []}
    results = {}
    for arm in ("cold", "warm"):
        def feedback(case, action, arm=arm):
            seen[arm].append((case, action))
            return world.feedback(case, -action)

        result = discover(
            probe_ids=train, observe=world.observe, reward=feedback,
            budget=budget, seed=world_id,
            prior_rule=prior if arm == "warm" else None,
        )
        rule = result["selected_rule"]
        correct = sum(
            rule is not None and
            act(rule, world.observe(case)) == -world.correct_action(case)
            for case in blind
        )
        results[arm] = {
            "correct": correct, "attempted": len(blind) if rule else 0,
            "abstained": len(blind) if rule is None else 0,
            "reward_calls": result["reward_calls"],
            "probes_used": result["probes_used"],
            "selected_rule": rule,
            "probe_ids": [row["probe_id"] for row in result["records"]],
            "prior_guided": result["prior_guided_probe_selection"],
        }
    return {
        "world": world_id, "budget": budget, "status": "measured",
        "prior": prior, "arms": results,
        "prior_blind_correct_after_reversal": sum(
            act(prior, world.observe(case)) == -world.correct_action(case)
            for case in blind
        ),
        "training_reward_calls": {arm: len(calls) for arm, calls in seen.items()},
        "blind_used_for_training": False,
        "prior_source": "same_trial_synthetic_feedback_not_restored_core_memory",
        "prior_train_blind_sensor_disjoint": True,
    }


class PairedRuleReversalTests(unittest.TestCase):
    def test_matched_feedback_and_withheld_reversal(self):
        rows = [reversal_trial(world, budget)
                for world in (120, 121, 122, 123)
                for budget in (4, 12)]
        measured = [row for row in rows if row["status"] == "measured"]
        self.assertGreater(len(measured), 0)
        for row in measured:
            cold, warm = row["arms"]["cold"], row["arms"]["warm"]
            self.assertEqual(cold["reward_calls"], warm["reward_calls"])
            self.assertEqual(cold["reward_calls"], row["budget"] * 3)
            self.assertEqual(row["training_reward_calls"]["cold"],
                             row["training_reward_calls"]["warm"])
            self.assertEqual(cold["probes_used"], row["budget"])
            self.assertEqual(warm["probes_used"], row["budget"])
            self.assertEqual(cold["attempted"] + cold["abstained"], 48)
            self.assertEqual(warm["attempted"] + warm["abstained"], 48)
            self.assertFalse(row["blind_used_for_training"])
            self.assertTrue(row["prior_train_blind_sensor_disjoint"])
            self.assertEqual(row["prior_source"],
                             "same_trial_synthetic_feedback_not_restored_core_memory")
            if row["budget"] == 12:
                self.assertEqual(cold["probe_ids"], warm["probe_ids"])
                self.assertFalse(warm["prior_guided"])
            else:
                self.assertTrue(warm["prior_guided"])
        # Emit actual per-world scores for CI logs, including losses and ties.
        # No assertion of a learning advantage: negative results are valid.
        print("PAIRED_RULE_REVERSAL " + json.dumps(rows, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
