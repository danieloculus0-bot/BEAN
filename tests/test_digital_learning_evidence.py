"""Guard against mistaking ablation gains for evidence of learning."""
import json
import unittest
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "research/github_brain/manifest.json"


def assess_learning_evidence(learning):
    """Compare candidate to strongest available control, not weakest ablation."""
    n = learning["blind_cases_total"]
    candidate = learning["candidate_correct_total"]
    controls = {key: learning[key] for key in (
        "grammar_matched_correct_total", "passive_correct_total",
        "memory_ablated_correct_total", "shuffled_correct_total"
    ) if key in learning}
    if type(n) is not int or n <= 0:
        raise ValueError("invalid evaluation count")
    if type(candidate) is not int or not 0 <= candidate <= n:
        raise ValueError("invalid candidate score")
    if not controls or any(type(v) is not int or not 0 <= v <= n for v in controls.values()):
        raise ValueError("missing or invalid controls")
    strongest = max(controls.values())
    return {
        "candidate": candidate,
        "strongest_control": strongest,
        "advantage_cases": candidate - strongest,
        "positive_advantage": candidate > strongest,
        "independently_audited": learning.get("independently_audited") is True,
    }


class DigitalLearningEvidenceTests(unittest.TestCase):
    def test_tied_strong_controls_not_learning_advantage(self):
        evidence = dict(blind_cases_total=144, candidate_correct_total=144,
                        grammar_matched_correct_total=144, passive_correct_total=144,
                        memory_ablated_correct_total=96, independently_audited=False)
        result = assess_learning_evidence(evidence)
        self.assertEqual(result["advantage_cases"], 0)
        self.assertFalse(result["positive_advantage"])
        self.assertFalse(result["independently_audited"])

    def test_weak_ablation_does_not_hide_stronger_control(self):
        result = assess_learning_evidence(dict(blind_cases_total=10, candidate_correct_total=8,
                                               memory_ablated_correct_total=2,
                                               passive_correct_total=9))
        self.assertEqual(result["advantage_cases"], -1)

    def test_positive_advantage_not_independent_proof(self):
        result = assess_learning_evidence(dict(blind_cases_total=10, candidate_correct_total=9,
                                               passive_correct_total=5))
        self.assertTrue(result["positive_advantage"])
        self.assertFalse(result["independently_audited"])

    def test_invalid_scores_rejected(self):
        for n, score in [(0, 0), (10, 11), (10, True)]:
            with self.subTest(n=n, score=score), self.assertRaises(ValueError):
                assess_learning_evidence(dict(blind_cases_total=n,
                                              candidate_correct_total=score,
                                              passive_correct_total=0))

    @unittest.skipUnless(MANIFEST.is_file(), "GitHub manifest unavailable in isolated checkout")
    def test_current_manifest_consistency(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        learning = manifest["digital_learning"]
        self.assertEqual(learning["generation"], manifest["generation"])
        self.assertEqual(learning["source_sha"], manifest["source_sha"])
        result = assess_learning_evidence(learning)
        self.assertEqual(result["candidate"], learning["candidate_correct_total"])


if __name__ == "__main__":
    unittest.main()
