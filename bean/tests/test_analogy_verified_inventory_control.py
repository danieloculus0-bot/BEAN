"""Evidence-inventory gate for synthetic analogy evaluation.

Separate from the legacy score_decisions diagnostic so the negative control
continues to document its false-positive behavior. Not a runtime retriever.
"""
import unittest

from bean.tests.test_analogy_selective_risk_control import score_decisions


def score_verified_decisions(gold, predictions, inventory):
    """Score only decisions supported by the independently supplied inventory.

    Inventory maps each task to {receipt_id: sha256_hex}. A gold receipt absent
    from the inventory invalidates the evaluation rather than silently treating
    an impossible label as truth. A prediction with absent/mismatched provenance
    is a wrong decision, never a correct retrieval. Predictions are (id, hash)
    tuples or None. Abstention is correct only when gold is None.
    """
    if not gold or set(gold) != set(predictions) or set(gold) != set(inventory):
        raise ValueError("nonempty matching task inventories required")
    normalized = {}
    invalid = []
    for task, expected in gold.items():
        candidates = inventory[task]
        if not isinstance(candidates, dict):
            raise ValueError("candidate inventory must map IDs to hashes")
        if expected is not None and expected not in candidates:
            raise ValueError("gold evidence absent from candidate inventory")
        choice = predictions[task]
        if choice is None:
            normalized[task] = None
            continue
        if (not isinstance(choice, tuple) or len(choice) != 2
                or not isinstance(choice[0], str)
                or not isinstance(choice[1], str)
                or candidates.get(choice[0]) != choice[1]):
            invalid.append(task)
            normalized[task] = "__INVALID_PROVENANCE__"
        else:
            normalized[task] = choice[0]
    # Never allow an invalid prediction to accidentally match an external ID.
    if "__INVALID_PROVENANCE__" in {x for x in gold.values() if x is not None}:
        raise ValueError("reserved evidence identifier")
    result = score_decisions(gold, normalized)
    result["invalid_provenance_tasks"] = tuple(invalid)
    return result


class VerifiedCandidateControl(unittest.TestCase):
    A = "a" * 64
    B = "b" * 64

    def test_missing_gold_rejected_not_perfect(self):
        with self.assertRaisesRegex(ValueError, "gold evidence absent"):
            score_verified_decisions(
                {"t": "missing"}, {"t": ("missing", self.A)},
                {"t": {"available": self.A}},
            )

    def test_forged_receipt_and_hash_do_not_earn_credit(self):
        gold = {"valid": "r1", "wrong-hash": "r1", "abstain": None}
        inventory = {t: {"r1": self.A} for t in gold}
        predicted = {
            "valid": ("r1", self.A),
            "wrong-hash": ("r1", self.B),
            "abstain": None,
        }
        result = score_verified_decisions(gold, predicted, inventory)
        self.assertEqual(result["decision_accuracy"], 2 / 3)
        self.assertEqual(result["coverage"], 2 / 3)
        self.assertEqual(result["invalid_provenance_tasks"], ("wrong-hash",))

    def test_missing_predicted_receipt_not_credit(self):
        result = score_verified_decisions(
            {"t": "r1"}, {"t": ("phantom", self.A)},
            {"t": {"r1": self.A}},
        )
        self.assertEqual(result["decision_accuracy"], 0.0)

    def test_inventory_keys_must_match(self):
        with self.assertRaises(ValueError):
            score_verified_decisions({"t": None}, {"t": None}, {})


if __name__ == "__main__":
    unittest.main()
