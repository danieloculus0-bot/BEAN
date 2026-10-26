"""Blind experiment for discovered *raw* concepts rather than assigned roles."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from bean.learning.experimental import ExperienceBank
from bean.evaluation.abstract_nonlinear_transfer import (
    TRAIN_SEEDS, make_ideas, ideas_features,
)
from bean.evaluation.raw_concept_induction import (
    SCHEMA, EXPRS, DEFAULT, WIRING_A, WIRING_B, BLIND, DEVELOPMENT,
    raw_observations, generate_program_primitives,
    evaluate_expression, choice_from_raw, simulate,
    fit_program, run_experiment,
)


class RawConceptInductionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.db = self.root / "bean-learning.sqlite3"

    def test_grammar_is_generated_and_no_target_roles_are_observed(self):
        world = make_ideas(93001)
        masked = raw_observations(world, WIRING_A)
        self.assertEqual(masked[0][0], 0)
        self.assertEqual(len(masked), len(world["experiments"]))
        self.assertEqual(len(masked[0][1]), 4)
        self.assertEqual(len(masked[0]), 4)
        self.assertEqual(EXPRS, generate_program_primitives())
        self.assertGreater(len(EXPRS), 30)
        self.assertEqual(len(EXPRS), len(set(EXPRS)))
        self.assertNotEqual(masked,
                            raw_observations(world, WIRING_B))
        self.assertTrue(all(isinstance(x, float) for x in masked[0][1]))
        self.assertNotEqual(
            tuple(masked[0][1]),
            tuple(ideas_features(world)[0][name] for name
                  in ("need", "leverage", "cost", "uncertainty")))
        with self.assertRaisesRegex(ValueError, "four-channel"):
            raw_observations(world, (0,1,1,3))
        assert all(isinstance(expr, tuple) and len(expr) == 3
                   for expr in EXPRS)

    def test_generated_programs_act_on_raw_observations(self):
        world = make_ideas(93012)
        rows = raw_observations(world, WIRING_A)
        group_max = {}
        for _, x, group, _ in rows:
            for i, value in enumerate(x):
                group_max[(group,i)] = max(
                    group_max.get((group,i), 0.), value)
        state = (rows[0][1],rows[0][2],rows[0][3])
        outcomes = [evaluate_expression(e, state, group_max) for e in EXPRS]
        self.assertTrue(all(0 <= x <= 1.0000001 for x in outcomes))
        self.assertGreater(len(set(round(x,6) for x in outcomes)), 12)
        self.assertIn(choice_from_raw(world,DEFAULT,WIRING_A),
                      range(len(world["experiments"])))

    def test_development_only_induces_new_source_guided_expressions(self):
        fit = fit_program(tuple(range(93000,93016)), WIRING_A)
        self.assertEqual(len(fit["program"]), 3)
        self.assertGreater(fit["independent_programs_evaluated"], 50)
        self.assertGreater(fit["development_rollouts"], 50*16)
        self.assertTrue(math.isfinite(fit["development_mean"]))
        self.assertTrue(all(tuple(expr) in EXPRS for expr in fit["program"]))
        self.assertGreaterEqual(
            fit["development_mean"],
            sum(simulate(seed,DEFAULT,WIRING_A) for seed in range(93000,93016))/16
            - 0.000001)

    def test_persist_new_concepts_and_score_unseen_raw_state(self):
        first = run_experiment(
            self.db,source_seeds=range(800,816),
            development=range(93000,93016),
            blind=range(104000,104032),wiring=WIRING_A)
        self.assertEqual(first["source_selected_policy"], "balanced")
        self.assertEqual(first["development_cases"], 16)
        self.assertEqual(first["blind_cases"], 32)
        self.assertTrue(first["engineer_authored_expression_grammar"])
        self.assertFalse(first["raw_semantic_role_mapping_supplied"])
        self.assertFalse(first["blind_rewards_available_at_selection"])
        self.assertEqual(set(first["blind_means"]), {
            "learned_raw", "naive_raw", "raw_urgency",
            "random", "engineered_concepts"})
        self.assertEqual(
            sum(first[k] for k in (
                "win_count_vs_naive_raw", "loss_count_vs_naive_raw",
                "tie_count_vs_naive_raw")),32)
        self.assertNotEqual(first["origin_journal_tip_before_blind"],
                            first["journal_tip_after_blind"])
        bank = ExperienceBank(self.db)
        try:
            trial=[e["data"] for e in bank.journal.events()
                   if e["kind"] == "trial"]
            self.assertEqual([r["phase"] for r in trial],
                             ["source_selection","raw_program_selection",
                              "post_program_blind_evaluation"])
            self.assertEqual(trial[1]["program"], first["learned_raw_program"])
            self.assertEqual(trial[2]["report_hash"],first["report_hash"])
        finally:
            bank.close()

    def test_sensor_swap_new_codebook_and_disjoint_holdout(self):
        seeds=range(93000,93016)
        a=fit_program(seeds,WIRING_A)
        b=fit_program(seeds,WIRING_B)
        self.assertEqual(a["candidate_expressions_generated"],
                         b["candidate_expressions_generated"])
        self.assertNotEqual(a["program"],b["program"])
        for args in (
            {"development": range(800,816),
             "blind": range(104000,104032)},
            {"development": [93000]*16,
             "blind": range(104000,104032)},
            {"development": range(93000,93016),
             "blind": range(93000,93032)},
        ):
            with self.assertRaisesRegex(ValueError, "disjoint"):
                run_experiment(self.db, source_seeds=range(800,816),**args)
        self.assertFalse(self.db.exists())


if __name__ == "__main__":
    unittest.main()
