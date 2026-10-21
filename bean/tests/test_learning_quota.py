"""Independent, signed bug-fix-credit accounting for 3,000-run experiments."""
import hashlib
import unittest
from bean.optimization.learning_quota import (
    evaluator_sign, unsigned_receipt, quota, verify_evaluator)

KEY=b"synthetic-test-verifier-external-key-not-for-use-in-production"


def hexhash(s):
    return hashlib.sha256(s.encode()).hexdigest()


def credit(bug_id="sample-01"):
    return unsigned_receipt(
        bug_id=bug_id,task="Axiom isolated scheduling fixture",
        patch_sha256=hexhash("verified patch "+bug_id),
        failing_test_sha256=hexhash("failing test "+bug_id),
        passing_test_sha256=hexhash("passing test "+bug_id),
        baseline_revision="bad-commit",fixed_revision="good-commit",
        proposed_by="BEAN",fixed_by="BEAN",
        independent_evaluator="external-CI-verifier",
        report_reference="https://github.com/example/research/actions/runs/123")


class QuotaTests(unittest.TestCase):
    def test_no_fabricated_bugfix_on_already_completed_3000(self):
        value=quota(q_episodes=3000)
        self.assertEqual(value["remaining"],0)
        self.assertEqual(value["actual_q_episodes"],3000)
        self.assertEqual(value["independently_verified_BEAN_bug_fixes"],0)

    def test_one_independently_signed_bean_fix_subtracts_exactly_one_run(self):
        signed=evaluator_sign(credit(),KEY)
        self.assertEqual(verify_evaluator(signed,KEY)["bug_id"],"sample-01")
        value=quota(q_episodes=2999,repair_receipts=[signed],
                    evaluator_key=KEY)
        self.assertEqual(value["target"],3000)
        self.assertEqual(value["credited_units"],3000)
        self.assertEqual(value["remaining"],0)
        self.assertEqual(value["actual_q_episodes"],2999)
        self.assertEqual(value["independently_verified_BEAN_bug_fixes"],1)

    def test_unsigned_wrong_key_and_tampering_never_earn_points(self):
        plain=credit()
        with self.assertRaisesRegex(ValueError,"key required"):
            quota(q_episodes=2999,repair_receipts=[plain])
        with self.assertRaises(ValueError):
            quota(q_episodes=2999,repair_receipts=[plain],evaluator_key=KEY)
        signed=evaluator_sign(plain,KEY)
        with self.assertRaisesRegex(ValueError,"signature"):
            quota(q_episodes=2999,repair_receipts=[signed],
                  evaluator_key=b"different-test-key-that-is-32-bytes-long")
        doctored={"claim":dict(signed["claim"]), "hmac_sha256":signed["hmac_sha256"]}
        doctored["claim"]["fixed_revision"]="changed_after_signature"
        with self.assertRaisesRegex(ValueError,"signature"):
            quota(q_episodes=2999,repair_receipts=[doctored],evaluator_key=KEY)

    def test_no_credit_for_human_or_assistant_repair(self):
        evidence=credit()
        evidence["fixed_by"]="ASSISTANT"
        with self.assertRaisesRegex(ValueError,"cannot earn"):
            evaluator_sign(evidence,KEY)
        evidence=credit()
        evidence["independent_evaluator"]="BEAN"
        with self.assertRaisesRegex(ValueError,"not independent"):
            evaluator_sign(evidence,KEY)

    def test_duplicate_credit_rejected_instead_of_doubling(self):
        signed=evaluator_sign(credit(),KEY)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            quota(q_episodes=2998,
                  repair_receipts=[signed,signed],evaluator_key=KEY)

    def test_original_q_count_is_not_replaced_or_lost(self):
        signed=evaluator_sign(credit(),KEY)
        p=quota(q_episodes=3000,repair_receipts=[signed],evaluator_key=KEY)
        self.assertEqual(p["actual_q_episodes"],3000)
        self.assertEqual(p["independently_verified_BEAN_bug_fixes"],1)
        self.assertEqual(p["remaining"],0)
        self.assertEqual(p["excess_learning_episodes"],1)
        self.assertEqual(p["credited_units"],3000)

if __name__=="__main__":
    unittest.main()
