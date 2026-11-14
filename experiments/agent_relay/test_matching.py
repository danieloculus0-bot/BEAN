"""Synthetic controls for reciprocal weighting, immediate search and re-scans."""
from __future__ import annotations

import unittest

from .ranking import FACTOR_WEIGHTS, FactorObservation, compute_fit, EvidenceLedger
from .discovery import AnonymousCandidate, DiscoveryIndex, schedule_followups


class WeightedMatchingTests(unittest.TestCase):
    def test_weights_sum_and_mutual_attraction_penalizes_one_way(self):
        self.assertAlmostEqual(sum(FACTOR_WEIGHTS.values()), 1)
        mutual = compute_fit({"mutual_attraction": FactorObservation(.9, .9)})
        asymmetric = compute_fit({"mutual_attraction": FactorObservation(.9, .1)})
        self.assertGreater(mutual["fit_index"], asymmetric["fit_index"])
        self.assertEqual(mutual["factor_coverage_pct"], 19.0)
        self.assertIsNone(mutual["calibrated_probability"])

    def test_unknown_is_unknown_not_zero(self):
        empty = compute_fit({})
        self.assertIsNone(empty["fit_index"])
        self.assertEqual(empty["factor_coverage_pct"], 0)
        one_sided = compute_fit({
            "communication": FactorObservation(.95, None)})
        self.assertIsNone(one_sided["fit_index"])
        known = compute_fit({"communication": FactorObservation(.95, .95)})
        self.assertGreater(known["fit_index"], 50)
        self.assertLess(known["factor_coverage_pct"], 100)
        self.assertGreater(known["provisional_upper_bound"], known["fit_index"])

    def test_custom_weights_without_predetermined_compatibility(self):
        w = {factor: 0.0 for factor in FACTOR_WEIGHTS}
        w["long_term_goals"] = 1.0
        scored = compute_fit({"long_term_goals": FactorObservation(.7, .8)}, weights=w)
        self.assertEqual(scored["factor_coverage_pct"], 100)
        self.assertAlmostEqual(scored["fit_index"], 74.83, places=2)
        with self.assertRaises(ValueError):
            compute_fit({}, weights={"communication": 1})
        with self.assertRaises(ValueError):
            FactorObservation(float("nan"), .9)

    def test_repeat_conversations_allow_revision_not_double_credit(self):
        history = EvidenceLedger()
        first = FactorObservation(.9, .8, .6)
        revised = FactorObservation(.3, .4, .9)
        self.assertTrue(history.observe("candidate_1", "communication", first,
                                        receipt_id="round_001"))
        self.assertFalse(history.observe("candidate_1", "communication", first,
                                         receipt_id="round_001"))
        self.assertEqual(history.conversation_count("candidate_1"), 1)
        before = history.score("candidate_1")["fit_index"]
        self.assertTrue(history.observe("candidate_1", "communication", revised,
                                        receipt_id="round_002"))
        self.assertEqual(history.conversation_count("candidate_1"), 2)
        self.assertLess(history.score("candidate_1")["fit_index"], before)
        with self.assertRaises(ValueError):
            history.observe("candidate_1", "communication", revised,
                            receipt_id="round_001")

    def test_instant_count_of_64000_synthetic_candidates(self):
        ix = DiscoveryIndex()
        tags = frozenset({("hobbies", "creative_making"),
                          ("communication", "direct_talk")})
        for i in range(64000):
            ix.upsert(AnonymousCandidate("synthetic-%06d" % i, tags,
                                         ready=True, active=True,
                                         consent=True, adult_confirmed=True))
        ix.upsert(AnonymousCandidate("opted-out", tags, ready=True, active=True,
                                     consent=False, adult_confirmed=True))
        ix.upsert(AnonymousCandidate("underage", tags, ready=True, active=True,
                                     consent=True, adult_confirmed=False))
        result = ix.search(frozenset({("hobbies", "creative_making")}), limit=5)
        self.assertEqual(result["registered_agents"], 64002)
        self.assertEqual(result["eligible_opted_in_agents_worldwide"], 64000)
        self.assertEqual(result["preliminary_candidates"], 64000)
        self.assertEqual(len(result["shortlist"]), 5)
        self.assertEqual(result["deep_agent_conversations_completed"], 0)
        self.assertIsNone(result["verified_romantic_matches"])
        ix.upsert(AnonymousCandidate("synthetic-000001", tags, ready=False,
                                     active=True, consent=True, adult_confirmed=True))
        self.assertEqual(ix.search(frozenset(tags))["preliminary_candidates"], 63999)

    def test_progressive_probe_budget_and_revisit_not_auto_contacts(self):
        candidates = [
            {"agent_id": "match-1", "fit_index": 93,
             "factor_coverage_pct": 80, "conversations": 2},
            {"agent_id": "match-2", "fit_index": 85,
             "factor_coverage_pct": 12, "conversations": 0},
            {"agent_id": "match-3", "fit_index": 55,
             "factor_coverage_pct": 2, "conversations": 1},
        ]
        early = schedule_followups(days_searching=0, scored_candidates=candidates)
        later = schedule_followups(days_searching=42, scored_candidates=candidates)
        self.assertGreater(later["probe_budget"], early["probe_budget"])
        self.assertEqual(later["contacts_sent"], 0)
        self.assertEqual(early["planned_probes"][0]["agent_id"], "match-1")
        self.assertEqual(early["planned_probes"][0]["action"], "repeat_interview")
        self.assertEqual({x["agent_id"] for x in early["planned_probes"]},
                         {"match-1", "match-2", "match-3"})

    def test_undisclosed_sensitive_free_text_rejected_at_index(self):
        with self.assertRaises(ValueError):
            AnonymousCandidate("candidate", frozenset({
                ("mental_health", "private")}), True, True, True, True)
        with self.assertRaises(ValueError):
            AnonymousCandidate("candidate", frozenset({
                ("hobbies", "my private secret")}), True, True, True, True)


if __name__ == "__main__":
    unittest.main()
