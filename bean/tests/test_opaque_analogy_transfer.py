"""Source-learned policy + unknown target binding, scored against strong controls."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from bean.evaluation.opaque_analogy_transfer import (
    SCHEMA, ROLES, ALL_BINDINGS, DEFAULT_WIRING, ALTERNATE_WIRING,
    opaque_target_observations, evaluate_bindings, replay, run_experiment,
    retain_binding, recover_binding, select_from_channels,
)
from bean.evaluation.abstract_nonlinear_transfer import (
    TRAIN_SEEDS, make_ideas, compare, learn_principle, recover_principle,
)
from bean.learning.experimental import ExperienceBank


class OpaqueAnalogyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / "experience.sqlite3"

    def test_encoder_exposes_numeric_channels_without_semantic_names(self):
        obs = opaque_target_observations(make_ideas(7000), DEFAULT_WIRING)
        self.assertEqual(len(obs), 9)
        self.assertEqual(set(ROLES), {
            "need", "leverage", "cost", "uncertainty", "near_tip"})
        self.assertEqual(len(ALL_BINDINGS), 120)
        for identifier, vector in obs:
            self.assertIsInstance(identifier, int)
            self.assertEqual(len(vector), 5)
            self.assertTrue(all(isinstance(x, float) and 0 <= x <= 1
                                for x in vector))
        self.assertNotEqual(obs, opaque_target_observations(
            make_ideas(7000), ALTERNATE_WIRING))
        with self.assertRaises(ValueError):
            opaque_target_observations(make_ideas(7000), (1,1,2,3,4))
        with self.assertRaises(ValueError):
            select_from_channels("balanced", obs, (0,0,1,2,3))

    def test_learner_ranks_every_permutation_on_identical_development_cases(self):
        obs = lambda world: opaque_target_observations(world, DEFAULT_WIRING)
        scores = evaluate_bindings(tuple(range(71000,71016)), "balanced", obs)
        self.assertEqual(len(scores), 120)
        self.assertEqual({tuple(x["binding"]) for x in scores}, set(ALL_BINDINGS))
        self.assertTrue(all(r["cases"] == 16 for r in scores))
        self.assertEqual(scores, evaluate_bindings(
            tuple(range(71000,71016)), "balanced", obs))
        self.assertGreaterEqual(scores[0]["mean_reward"], scores[-1]["mean_reward"])

    def test_replay_and_journal_durability_on_first_sensor_wiring(self):
        result = run_experiment(
            self.db, source_seeds=range(800,816),
            development=range(71000,71016), blind=range(82000,82048),
            wiring=DEFAULT_WIRING)
        self.assertEqual(result["source_training_cases"], 16)
        self.assertEqual(result["development_cases"], 16)
        self.assertEqual(result["blind_cases"], 48)
        self.assertEqual(result["binding_search_candidates"], 120)
        self.assertEqual(result["source_prior_search_reduction_factor"], 6)
        self.assertEqual(result["source_prior_candidate_evaluations"], 120*16)
        self.assertEqual(result["target_only_candidate_evaluations"], 720*16)
        self.assertFalse(result["observation_wiring_exposed_to_learner"])
        self.assertTrue(result["engineered_target_observation_channels"])
        self.assertFalse(result["blind_used_in_model_selection"])
        self.assertTrue(all(math.isfinite(x) for x in result["blind_means"].values()))
        self.assertNotEqual(result["ledger_tip_after_blind"],
                            result["ledger_tip_before_blind"])
        bank = ExperienceBank(self.db)
        try:
            self.assertEqual(recover_binding(bank)["selected_binding"],
                             result["retained_binding"])
            self.assertEqual(recover_principle(bank), result["source_selected_policy"])
            self.assertEqual([e["data"]["phase"] for e in bank.journal.events()],
                             ["source_selection", "development_binding_selection",
                              "post_selection_blind_scoring"])
        finally:
            bank.close()

    def test_new_sensor_wiring_forces_new_binding_inference(self):
        same_seed_source=range(800,816)
        dev=range(71000,71016)
        blind=range(82000,82048)
        a = run_experiment(
            self.db, source_seeds=same_seed_source,
            development=dev, blind=blind, wiring=DEFAULT_WIRING)
        b = run_experiment(
            self.root / "alternate.sqlite3",
            source_seeds=same_seed_source,
            development=dev, blind=blind, wiring=ALTERNATE_WIRING)
        self.assertEqual(a["source_selected_policy"], b["source_selected_policy"])
        self.assertNotEqual(a["retained_binding"], b["retained_binding"])
        self.assertEqual(set(a["blind_means"]), set(b["blind_means"]))
        self.assertEqual(a["binding_search_candidates"], 120)

    def test_overlap_repeats_or_short_development_cannot_score(self):
        for kwargs in (
            {"development": range(800,816), "blind": range(82000,82048)},
            {"development": [71000]*16, "blind": range(82000,82048)},
            {"development": range(71000,71016), "blind": range(71000,71032)},
            {"development": range(71000,71004), "blind": range(82000,82048)},
        ):
            with self.assertRaisesRegex(ValueError, "distinct disjoint"):
                run_experiment(self.db, source_seeds=range(800,816), **kwargs)
        self.assertFalse(self.db.exists())


if __name__ == "__main__":
    unittest.main()
