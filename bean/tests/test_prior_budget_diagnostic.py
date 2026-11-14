"""Regression diagnostic: standard-budget probes cannot use the prior rule.

This is a negative control, not a demonstration of retained learning.
The existing discover() implementation deliberately switches to generic
disagreement for budgets > 6. We document that causal limitation with
a deterministic comparison before attempting a reversal benchmark.
"""
import unittest

from bean.evaluation.active_abstraction_benchmark import World
from bean.learning.active_hypothesis import discover, generate


class PriorBudgetDiagnostic(unittest.TestCase):
    def test_standard_budget_prior_does_not_change_probe_selection(self):
        world = World(120, "channel")
        probes = [str(100 + i) for i in range(40)]
        validation = [str(1000 + i) for i in range(8)]
        options = dict(
            probe_ids=probes,
            validation_probe_ids=validation,
            observe=world.observe,
            reward=world.feedback,
            budget=12,
            method="disagreement",
            seed=120,
        )
        cold = discover(**options)
        # Choose a valid but deliberately different prior. Under the
        # standard 12-probe budget, the prior cannot influence sampling.
        prior = generate(4)[-1]
        warm = discover(**options, prior_rule=prior)
        self.assertEqual(cold["probes_used"], warm["probes_used"])
        self.assertEqual(cold["reward_calls"], warm["reward_calls"])
        self.assertEqual(cold["selected_rule"], warm["selected_rule"])

    def test_low_budget_remains_bounded_and_has_no_free_feedback(self):
        world = World(120, "channel")
        probes = [str(100 + i) for i in range(40)]
        options = dict(
            probe_ids=probes,
            observe=world.observe,
            reward=world.feedback,
            budget=4,
            method="disagreement",
            seed=120,
        )
        cold = discover(**options)
        warm = discover(**options, prior_rule=generate(4)[-1])
        self.assertEqual(cold["reward_calls"], warm["reward_calls"])
        self.assertEqual(cold["probes_used"], 4)
        self.assertEqual(warm["probes_used"], 4)
        # No assertion of advantage: different probes are not proof of
        # better adaptation. That requires paired unseen reversal worlds.


if __name__ == "__main__":
    unittest.main()
