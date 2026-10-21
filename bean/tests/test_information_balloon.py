"""Independent synthetic tests for BEAN Information Balloon compression lab."""
from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path
import unittest

from bean.optimization.information_balloon import (
    Recipe, benchmark_once, canonical, contextual_recall, digest,
    discover_tokens, fit_prefix, growth_experiment, pack, propose, retain_verified, run_experiment,
    token_decode, token_encode, unpack, weissman_style,
)


def fixtures(n=24):
    return [{"id":f"receipt_{i:03d}",
             "text": ("torque_witness verified_alignment " * (15 + i % 4) +
                      f"source-id={i} FAILURE_TAG" + (" \u2603" if i % 3 else "")),
             "tags":[f"topic_{i % 4}", "evidence", "defect" if i % 3 else "pass"]}
            for i in range(n)]


class BalloonTests(unittest.TestCase):
    def test_reversible_handmade_dictionary_and_binary_edge_cases(self):
        blob = (b"\x00\xff\x00NAME=TOLERANCE;NAME=TOLERANCE;" * 31 +
                bytes(range(256)) * 2)
        recipe = Recipe("zlib", 6, 8, 16)
        tokens = discover_tokens(blob, recipe)
        self.assertTrue(tokens, "Research must create its own dictionary")
        self.assertEqual(token_decode(token_encode(blob, tokens),tokens,len(blob)),blob)
        archive = pack(blob,recipe,training=blob)
        self.assertEqual(unpack(archive),blob)
        self.assertEqual(digest(unpack(archive)),digest(blob))

    def test_backend_exactness_and_end_to_end_recovery(self):
        data = canonical(fixtures())
        for recipe in (Recipe("raw",0),Recipe("zlib",1),
                       Recipe("zlib",6,6,8),Recipe("zlib",9,12,32),
                       Recipe("bz2",1),Recipe("lzma",0)):
            with self.subTest(recipe=recipe):
                blob = pack(data,recipe,training=data)
                self.assertEqual(unpack(blob),data)
                self.assertEqual(unpack(blob,expected_hash=digest(blob)),data)
                self.assertGreater(len(blob),0)

    def test_detects_corruption_and_wrong_trust_anchor(self):
        data = canonical(fixtures())
        archive = pack(data,Recipe("zlib",6),training=data)
        altered = bytearray(archive)
        altered[-1] ^= 1
        with self.assertRaises(ValueError):
            unpack(bytes(altered))
        with self.assertRaisesRegex(ValueError,"trusted package"):
            unpack(archive,expected_hash="0"*64)
        signed = pack(data,Recipe("zlib",6,6,8),
                      training=data,key=b"local-secret-test-key-only")
        self.assertEqual(unpack(signed,key=b"local-secret-test-key-only"),data)
        with self.assertRaisesRegex(ValueError,"authentication"):
            unpack(signed,key=b"different-key-that-is-long")
        forged = bytearray(signed)
        forged[-8] ^= 1
        with self.assertRaisesRegex(ValueError,"authentication"):
            unpack(bytes(forged),key=b"local-secret-test-key-only")

    def test_cannot_claim_integrity_by_discarding_raw_bytes(self):
        source=canonical(fixtures())
        with self.assertRaisesRegex(ValueError,"source must"):
            pack("string pretending to be bytes",Recipe("zlib",6))
        with self.assertRaisesRegex(ValueError,"archive magic"):
            unpack(b"unverified compressed content")
        with self.assertRaises(ValueError):
            token_decode(b"\x00\xfe",[b"hello"],100)
        with self.assertRaises(ValueError):
            token_decode(b"\x00",[b"hello"],100)

    def test_weissman_diagnostic_is_finite_and_declared_not_canonical(self):
        self.assertAlmostEqual(weissman_style(2.0,2.0,4.0,4.0),1.0)
        self.assertGreater(weissman_style(3,2,4,4),1.0)
        with self.assertRaises(ValueError):
            weissman_style(2,2,0,1)

    def test_context_refs_respect_budget_and_exact_tags(self):
        data=fixtures()
        result=contextual_recall(data,["topic_0","topic_1"],budget=10000)
        self.assertEqual(result["mean_recall"],1.0)
        low=contextual_recall(data,["topic_0","topic_1"],budget=250)
        self.assertLess(low["mean_recall"],1.0)
        self.assertTrue(all(x["bytes"]<=250 for x in low["queries"]))

    def test_never_drop_excluded_retention_ids_silently(self):
        source=fixtures()
        training=canonical(source[:14])
        recipe=Recipe("zlib",6,6,8)
        full=fit_prefix(source,recipe,training,50000)
        self.assertTrue(full["all_retained"])
        self.assertEqual(json.loads(unpack(full["archive"])),source)
        partial=fit_prefix(source,recipe,training,500)
        self.assertFalse(partial["all_retained"])
        self.assertEqual(partial["retained"]+len(partial["excluded_ids"]),len(source))
        self.assertEqual(partial["excluded_ids"],
                         [r["id"] for r in source[partial["retained"]:]])
        self.assertEqual(source,fixtures(),"No source mutation or deletion allowed")

    def test_adaptive_trials_have_honest_heldout_and_negative_cases(self):
        source=fixtures()
        raw=canonical(source)
        result=run_experiment(source,archive_budget=60000,context_budget=12000,
                              queries=["topic_0","topic_1","topic_2","topic_3"],
                              min_recall=1,iterations=12,seed=9)
        self.assertTrue(result["accepted"],result["reason"])
        self.assertEqual(result["source_sha256"],digest(raw))
        self.assertEqual(result["working_shelf_records"],len(source))
        self.assertEqual(result["omitted_ids"],[])
        self.assertTrue(result["independent_holdout"]["exact"])
        self.assertEqual(result["candidate_count"],12)
        self.assertTrue(any(t["proposed_by"]=="self_dictionary" for t in result["trials"]))
        self.assertEqual(len(result["trials"]),12)
        self.assertTrue(all(t["phase"]=="tuning" and t["training_sha256"]
                            and t["tuning_sha256"] for t in result["trials"]))
        denied=run_experiment(source,archive_budget=150,context_budget=200,
                              queries=["topic_0"],min_recall=1,
                              iterations=9,seed=9)
        self.assertFalse(denied["accepted"])
        self.assertGreater(len(denied["omitted_ids"]),0)
        self.assertEqual(source,fixtures())

    def test_write_once_cold_storage_integrity_and_no_deletion(self):
        source=canonical(fixtures())
        with tempfile.TemporaryDirectory() as folder:
            key=b"synthetic-external-key-32bytes00!"
            root=Path(folder)
            result=retain_verified(root,source,Recipe("zlib",6,6,8),
                                   training=source,key=key)
            self.assertEqual(Path(result["raw_path"]).read_bytes(),source)
            self.assertEqual(result["receipt"]["integrity"],
                             "verified_against_immutable_original")
            self.assertEqual(
                retain_verified(root,source,Recipe("zlib",6,6,8),
                                training=source,key=key)["receipt"],
                result["receipt"])
            p=Path(result["package_path"])
            damaged=bytearray(p.read_bytes())
            damaged[-1]^=1
            p.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError,"retention conflict"):
                retain_verified(root,source,Recipe("zlib",6,6,8),
                                training=source,key=key)
            self.assertEqual(Path(result["raw_path"]).read_bytes(),source)
            self.assertTrue(Path(result["manifest_path"]).exists())

    def test_compression_meets_budget_without_maximizing_ratio(self):
        data=fixtures()
        result=run_experiment(data,archive_budget=40000,context_budget=10000,
                              queries=["topic_0"],min_recall=1,iterations=10,seed=4)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["selection_priority"],
                         "meet_storage_goal_then_minimize_encoding_latency")
        feasible=[t for t in result["trials"] if t.get("meets_estimated_rate_target")]
        self.assertTrue(feasible)
        self.assertTrue(all(t["metric"]["exact"] for t in feasible))
        self.assertEqual(result["omitted_ids"],[])

    def test_growth_adapts_with_measured_reverified_prior_policy(self):
        dataset=fixtures()
        progress=growth_experiment(
            dataset,checkpoints=[9,16,24],archive_budget=30000,
            context_budget=10000,queries=["topic_0","topic_1"],
            min_recall=1.0,iterations=10,seed=18)
        points=progress["snapshots"]
        self.assertEqual([x["source_records"] for x in points],[9,16,24])
        self.assertTrue(all(x["accepted"] for x in points))
        self.assertEqual([x["retained"] for x in points],[9,16,24])
        self.assertIsNone(points[0]["previous_recipe"])
        self.assertEqual(points[1]["previous_recipe"],points[0]["selected_recipe"])
        self.assertTrue(any(
            trial["proposed_by"]=="retained_previous_recipe_reverified"
            for trial in points[1]["all_trials"]))
        self.assertEqual(progress["source_records_total"],24)

    def test_recipe_validation_no_unsupported_lossy_encoder(self):
        for recipe in [Recipe("mp3",1),Recipe("raw",9),Recipe("zlib",6,4,0),
                       Recipe("lzma",6,6,8)]:
            with self.subTest(recipe=recipe):
                with self.assertRaises(ValueError):
                    recipe.validate()


if __name__ == "__main__":
    unittest.main()
