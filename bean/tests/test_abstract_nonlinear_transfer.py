"""Nonlinear cross-domain transfer: paired controls, separate task mechanics."""
from __future__ import annotations

from pathlib import Path
import json
import math
import tempfile
import unittest

from bean.learning.experimental import ExperienceBank
from bean.evaluation.abstract_nonlinear_transfer import (
    SCHEMA, POLICIES, BLIND_SEEDS, TRAIN_SEEDS, HORIZON,
    make_shop, make_ecosystem, make_ideas,
    shop_features, ecosystem_features, ideas_features,
    shop_utility, ecosystem_utility, ideas_utility,
    rollout, compare, means,
    learn_principle, recover_principle, run_experiment,
)


class PhilosophyOnlyTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "bean-original-journal.sqlite3"

    def test_distinct_source_target_state_and_two_non_linearities(self):
        shop = make_shop(811)
        reserve = make_ecosystem(11111)
        self.assertEqual(set(shop), {"plant", "stations", "routing", "temperature"})
        self.assertEqual(set(reserve), {"reserve", "guilds", "food_web", "weather"})
        self.assertFalse(set(shop) & set(reserve))
        sf = shop_features(shop)
        ef = ecosystem_features(reserve)
        self.assertEqual(set(sf[0]), set(ef[0]))
        self.assertEqual(set(sf[0]), {
            "id", "need", "leverage", "cost", "uncertainty", "near_tip"})
        # Nonlinear interactions are in both actual transition and objectives;
        # this is not a disguised linear regression on shared numeric columns.
        wear = shop["stations"][0]["wear"]
        shop["stations"][0]["wear"] = .1
        u1 = shop_utility(shop)
        shop["stations"][0]["wear"] = .3
        u2 = shop_utility(shop)
        shop["stations"][0]["wear"] = .5
        u3 = shop_utility(shop)
        self.assertNotAlmostEqual(u2-u1, u3-u2, places=5)
        shop["stations"][0]["wear"] = wear
        start = reserve["guilds"][0]["abundance"]
        reserve["guilds"][0]["abundance"] = .2
        e1 = ecosystem_utility(reserve)
        reserve["guilds"][0]["abundance"] = .4
        e2 = ecosystem_utility(reserve)
        reserve["guilds"][0]["abundance"] = .6
        e3 = ecosystem_utility(reserve)
        self.assertNotAlmostEqual(e2-e1, e3-e2, places=5)
        reserve["guilds"][0]["abundance"] = start

    def test_second_target_is_nonlinear_non_network_portfolio(self):
        target = make_ideas(18000)
        self.assertEqual(set(target), {
            "laboratory", "experiments", "funding_climate", "milestone"})
        self.assertFalse(set(target) & set(make_shop(810)))
        self.assertFalse(set(target) & set(make_ecosystem(11010)))
        self.assertEqual(set(ideas_features(target)[0]), {
            "id", "need", "leverage", "cost", "uncertainty", "near_tip"})
        # Portfolio-level synergy is nonlinear, despite zero graph edges.
        projects = target["experiments"]
        original = projects[0]["readiness"]
        projects[0]["readiness"] = .2
        v1 = ideas_utility(target)
        projects[0]["readiness"] = .4
        v2 = ideas_utility(target)
        projects[0]["readiness"] = .6
        v3 = ideas_utility(target)
        self.assertNotAlmostEqual(v2-v1, v3-v2, places=5)
        projects[0]["readiness"] = original

    def test_source_policy_retains_same_choice_for_unrelated_second_target(self):
        primary = run_experiment(
            self.database, source_seeds=range(800,816),
            blind_seeds=range(26000,26048),
            target_kind="ideas")
        self.assertEqual(primary["target_dataset"], "ideas-blind-v1")
        self.assertEqual(primary["source_cases"], 16)
        self.assertEqual(primary["target_cases"], 48)
        self.assertFalse(primary["target_feedback_used_in_selection"])
        self.assertTrue(primary["learned_policy_recovered_from_owned_journal"])
        self.assertEqual(len(primary["target_case_deltas"]), 48)
        self.assertEqual(
            sum(primary[k] for k in
                ("target_wins_vs_urgent", "target_losses_vs_urgent",
                 "target_ties_vs_urgent")), 48)
        self.assertIn(primary["selected_source_policy"], POLICIES)
        self.assertTrue(math.isfinite(primary["target_delta_vs_urgent"]))

    def test_identical_seeds_give_matched_policy_comparison(self):
        seeds = range(2010, 2020)
        rows = compare("shop", seeds)
        self.assertEqual(rows, compare("shop", seeds))
        self.assertEqual(len(rows), 10)
        self.assertEqual(set(rows[0]["rewards"]), {*POLICIES, "random"})
        self.assertTrue(all(math.isfinite(v)
                            for row in rows for v in row["rewards"].values()))
        self.assertEqual(len(rollout("ecosystem", 6001, "urgent")["actions"]),
                         HORIZON)
        self.assertNotEqual(rollout("shop", 6001, "urgent")["utility"],
                            rollout("ecosystem", 6001, "urgent")["utility"])

    def test_source_learning_recovers_immutable_selection_and_no_target(self):
        bank = ExperienceBank(self.database)
        try:
            source = compare("shop", range(800, 816))
            trial = learn_principle(bank, source)
            self.assertIn(trial["measured_selected_policy"], POLICIES)
            self.assertFalse(trial["target_feedback_available_at_selection"])
            self.assertEqual(recover_principle(bank), trial["measured_selected_policy"])
            original = bank.journal.export()
            self.assertEqual(len(original["events"]), 1)
            self.assertEqual(original["events"][0]["kind"], "trial")
        finally:
            bank.close()
        reopened = ExperienceBank(self.database)
        try:
            self.assertEqual(recover_principle(reopened), trial["measured_selected_policy"])
            self.assertEqual(reopened.journal.export()["tip"], original["tip"])
        finally:
            reopened.close()

    def test_blind_target_results_written_only_after_source_freeze(self):
        report = run_experiment(
            self.database, source_seeds=range(800, 816),
            blind_seeds=range(15000, 15048))
        self.assertEqual(report["source_cases"], 16)
        self.assertEqual(report["target_cases"], 48)
        self.assertEqual(len(report["target_case_deltas"]), 48)
        self.assertIn(report["selected_source_policy"], POLICIES)
        self.assertEqual(set(report["target_means"]), {*POLICIES, "random"})
        self.assertTrue(report["learned_policy_recovered_from_owned_journal"])
        self.assertFalse(report["target_feedback_used_in_selection"])
        self.assertTrue(report["domain_adapter_mapping_provided"])
        self.assertEqual(
            sum(report[k] for k in ("target_wins_vs_urgent",
                                    "target_losses_vs_urgent",
                                    "target_ties_vs_urgent")), 48)
        self.assertNotEqual(report["pre_target_ledger_tip"],
                            report["post_target_ledger_tip"])
        b = ExperienceBank(self.database)
        try:
            events = b.journal.events()
            self.assertEqual([e["data"]["phase"] for e in events],
                             ["source_selection", "blind_target_report"])
            self.assertEqual(
                events[1]["data"]["report_sha256"], report["report_sha256"])
        finally:
            b.close()

    def test_duplicate_ids_and_overlapping_blind_set_rejected(self):
        with self.assertRaisesRegex(ValueError, "disjoint"):
            run_experiment(self.database,
                           source_seeds=range(800,816),
                           blind_seeds=range(800,840))
        with self.assertRaisesRegex(ValueError, "distinct"):
            run_experiment(self.database,
                           source_seeds=range(800,816),
                           blind_seeds=[10]*48)
        self.assertFalse(self.database.exists())

    def test_holdout_scores_are_deterministic_and_comparable(self):
        a = run_experiment(self.database,
                           source_seeds=TRAIN_SEEDS,
                           blind_seeds=BLIND_SEEDS)
        second = Path(self.temp.name) / "replay.sqlite3"
        b = run_experiment(second, source_seeds=TRAIN_SEEDS, blind_seeds=BLIND_SEEDS)
        for key in ("source_cases", "target_cases", "source_means",
                    "selected_source_policy", "target_means",
                    "target_case_deltas", "target_delta_vs_urgent",
                    "target_delta_vs_random", "target_wins_vs_urgent",
                    "target_losses_vs_urgent", "target_ties_vs_urgent",
                    "report_sha256"):
            self.assertEqual(a[key], b[key])
        print("BEAN_ABSTRACTION_MATCHED_SCORE " + json.dumps({
            "selected_policy": a["selected_source_policy"],
            "target_cases": a["target_cases"],
            "target_delta_vs_urgent": a["target_delta_vs_urgent"],
            "target_delta_vs_random": a["target_delta_vs_random"],
            "target_wins_vs_urgent": a["target_wins_vs_urgent"],
            "target_losses_vs_urgent": a["target_losses_vs_urgent"],
            "mean_target_utilities": a["target_means"],
            "source_mean_utilities": a["source_means"],
            "heldout_feedback_in_training": False,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
