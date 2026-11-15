"""Regression checks for the evidence-backed challenge and explicit override contract."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bean.cognition.challenge_gate import ChallengeGate, Proposal
from bean.cognition.epistemic_guard import CandidateClaim, EpistemicGuard
from bean.memory.store import get_store, init_store


class ChallengePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        init_store(str(Path(self.temp.name) / "bean.sqlite3"))
        # A genuine persisted BEAN audit record, not a made-up reference.
        audit = EpistemicGuard().audit(CandidateClaim(
            key="proposal.risk",
            content="The expected behavior has not been verified.",
            source_type="synthetic_test",
            source_ref="synthetic:case-001",
            confidence=0.4,
            evidence=["synthetic:case-001"],
            falsification_path="Run the independent acceptance test.",
        ))
        self.ref = "epistemic_audit:" + audit.audit_id
        self.gate = ChallengeGate()
        self.proposal = Proposal("merge", "owner/repo#47", "a" * 40, "Fix verified regression")

    def tearDown(self):
        get_store().close()
        self.temp.cleanup()

    def objection(self):
        return [{"kind": "reckless", "reason": "Prior acceptance failed; merge would skip the retest.",
                 "evidence_refs": [self.ref]}]

    def test_clean_action_is_allowed_and_recorded(self):
        outcome = self.gate.review(self.proposal, [])
        self.assertEqual(outcome["decision"], "ALLOW")
        self.assertTrue(outcome["may_proceed"])
        self.assertEqual(len(self.gate.review(self.proposal, [])["objections"]), 0)

    def test_receipt_backed_objection_blocks_and_persists(self):
        blocked = self.gate.review(self.proposal, self.objection())
        self.assertEqual(blocked["decision"], "BLOCK")
        self.assertFalse(blocked["may_proceed"])
        self.assertEqual(blocked["objections"][0]["evidence_refs"], [self.ref])
        # Omitting an objection on replay cannot suppress the original stop.
        again = ChallengeGate().review(self.proposal, [])
        self.assertEqual(again["challenge_id"], blocked["challenge_id"])
        self.assertEqual(again["decision"], "BLOCK")
        self.assertEqual(len(get_store().fetchall("SELECT * FROM challenge_objections")), 1)

    def test_unknown_evidence_cannot_masquerade_as_receipt(self):
        false_ref = [{"kind": "conflict", "reason": "Contradictory result",
                      "evidence_refs": ["epistemic_audit:nonexistent"]}]
        with self.assertRaisesRegex(ValueError, "not found"):
            self.gate.review(self.proposal, false_ref)
        self.assertEqual(len(get_store().fetchall("SELECT * FROM challenge_reviews")), 0)

    def test_objection_without_evidence_is_not_recorded(self):
        objection = [{"kind": "reckless", "reason": "Just a hunch", "evidence_refs": []}]
        with self.assertRaisesRegex(ValueError, "actual BEAN evidence"):
            self.gate.review(self.proposal, objection)
        self.assertEqual(len(get_store().fetchall("SELECT * FROM challenge_reviews")), 0)

    def test_override_keeps_warning_and_actor_reason(self):
        blocked = self.gate.review(self.proposal, self.objection())
        allowed = self.gate.override(blocked["challenge_id"], actor="owner",
                                     justification="Proceed after accepting recorded risk")
        self.assertEqual(allowed["decision"], "OVERRIDDEN")
        self.assertTrue(allowed["may_proceed"])
        self.assertEqual(allowed["objections"], blocked["objections"])
        self.assertEqual(allowed["override"]["actor"], "owner")
        self.assertEqual(allowed["override"]["actor_authentication"],
                         "caller_supplied_not_authenticated_by_core")
        self.assertEqual(self.gate.review(self.proposal, [])["decision"], "OVERRIDDEN")
        with self.assertRaisesRegex(ValueError, "Already overridden"):
            self.gate.override(blocked["challenge_id"], actor="owner", justification="Repeat")

    def test_new_evidence_after_override_creates_new_block(self):
        first = self.gate.review(self.proposal, self.objection())
        self.gate.override(first["challenge_id"], actor="owner", justification="Risk accepted")
        new = self.gate.review(self.proposal, self.objection())
        self.assertEqual(new["decision"], "BLOCK")
        self.assertNotEqual(new["challenge_id"], first["challenge_id"])
        self.assertEqual(self.gate.status(first["challenge_id"])["decision"], "OVERRIDDEN")

    def test_revision_binding_and_no_override_of_allow(self):
        allowed = self.gate.review(self.proposal, [])
        with self.assertRaisesRegex(ValueError, "existing blocked"):
            self.gate.override(allowed["challenge_id"], actor="owner",
                               justification="No reason to override")
        blocked = self.gate.review(self.proposal, self.objection())
        different = Proposal("merge", "owner/repo#47", "b" * 40, "Fix verified regression")
        fresh = self.gate.review(different, [])
        self.assertEqual(fresh["decision"], "ALLOW")
        self.assertNotEqual(fresh["proposal_sha256"], blocked["proposal_sha256"])


if __name__ == "__main__":
    unittest.main()
