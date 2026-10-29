"""Contract tests for BEAN's opt-in local -> web -> feedback task loop.

These use synthetic HTTP/model/host-verifier fixtures. A host-reported pass
is not independently verified truth, model training or autonomous browsing.
"""
import tempfile
import unittest
from pathlib import Path

from bean.learning import NativeReasoningService
from bean.research import PublicWebSources, WebResearchService, register_web_research_handlers
from bean.tests.test_native_web_research import (
    FakeInternet, FakeInbox, ReasoningFixture, resolver,
)


class ResearchSolveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "solve.sqlite3"
        self.core = NativeReasoningService(self.db, model=ReasoningFixture())
        self.addCleanup(self.core.close)
        self.internet = FakeInternet()
        self.sources = PublicWebSources(
            brave_key="synthetic-fixture-key", request_fn=self.internet,
            resolver=resolver)
        self.service = WebResearchService(self.core, sources=self.sources)

    def run_task(self, **options):
        return self.service.solve_task(
            domain="inspection", task_ref="question-001",
            question="target inspection", provider="brave", **options)

    def trials(self):
        return [e["data"] for e in self.core.bank.journal.events()
                if e["kind"] == "trial" and e["data"].get("experiment")
                == "bean.native.research_solve.v1"]

    def test_native_solution_skips_network_and_inference(self):
        original = self.core.reason_local
        self.core.reason_local = lambda **_: {
            "status": "locally_solved", "answer": "native result"}
        try:
            answer = self.run_task(allow_external=True)
        finally:
            self.core.reason_local = original
        self.assertEqual(answer["status"], "locally_solved")
        self.assertEqual(answer["answer"], "native result")
        self.assertEqual(answer["network_requests"], 0)
        self.assertEqual(len(self.internet.calls), 0)
        self.assertFalse(answer["external_model_invoked"])
        self.assertEqual(len(self.trials()), 1)

    def test_without_consent_no_network_model_or_fabrication(self):
        answer = self.run_task()
        self.assertEqual(answer["status"], "external_research_disabled")
        self.assertIsNone(answer["answer"])
        self.assertFalse(answer["external_model_invoked"])
        self.assertEqual(self.sources.call_count, 0)
        self.assertEqual(len(self.trials()), 1)
        self.assertFalse(self.trials()[0]["external_research_authorized"])

    def test_gap_research_returns_unverified_answer_with_durable_receipts(self):
        answer = self.run_task(allow_external=True, max_pages=2)
        self.assertEqual(answer["status"], "candidate_unverified")
        self.assertEqual(answer["answer"], "RED")
        self.assertEqual(answer["source_count"], 2)
        self.assertEqual(answer["network_requests"], 3)
        self.assertEqual(len(answer["research_attempts"]), 1)
        self.assertTrue(answer["external_model_invoked"])
        self.assertFalse(answer["independently_authenticated"])
        self.assertTrue(answer["human_review_required"])
        original_tip = self.trials()[0]["research_attempts"][0]["inference_receipt"]
        self.assertTrue(original_tip)
        self.assertEqual(len([e for e in self.core.bank.journal.events()
                              if e["kind"] == "research"]), 1)
        self.core.close()
        reopened = NativeReasoningService(self.db)
        try:
            trials = [e["data"] for e in reopened.bank.journal.events()
                      if e["kind"] == "trial" and e["data"].get("experiment")
                      == "bean.native.research_solve.v1"]
            self.assertEqual(len(trials), 1)
            self.assertEqual(trials[0]["research_attempts"][0]["inference_receipt"],
                             original_tip)
        finally:
            reopened.close()

    def test_evidence_only_without_model_is_not_a_fake_answer(self):
        self.core.model = None
        answer = self.run_task(allow_external=True)
        self.assertEqual(answer["status"], "model_not_configured")
        self.assertEqual(answer["source_count"], 2)
        self.assertIsNone(answer["answer"])
        self.assertFalse(answer["external_model_invoked"])
        self.assertEqual(len(self.trials()), 1)

    def test_host_feedback_can_request_one_bounded_second_search(self):
        verdicts = []
        def host_check(*, answer, question, sources):
            verdicts.append((answer, question, len(sources)))
            return {"passed": len(verdicts) == 2,
                    "public_gap": "calibration certificate"}
        service = WebResearchService(
            self.core, sources=self.sources, trusted_verifier=host_check)
        answer = service.solve_task(
            domain="inspection", task_ref="feedback-loop",
            question="target inspection", provider="brave", max_pages=2,
            max_attempts=2, allow_external=True)
        self.assertEqual(answer["status"], "host_reported_pass")
        self.assertEqual(answer["network_requests"], 6)
        self.assertEqual(len(answer["research_attempts"]), 2)
        self.assertEqual([x["host_feedback"] for x in answer["research_attempts"]],
                         ["failed", "passed"])
        self.assertEqual(len(verdicts), 2)
        self.assertTrue(any("calibration" in url for url in self.internet.calls))
        self.assertEqual(len([e for e in self.core.bank.journal.events()
                              if e["kind"] == "research"]), 2)
        self.assertFalse(self.trials()[0]["final_answer_verified"])
        self.assertFalse(answer["independently_authenticated"])

    def test_negative_feedback_without_public_gap_stops_and_preserves_failure(self):
        service = WebResearchService(
            self.core, sources=self.sources,
            trusted_verifier=lambda **_: {"passed": False, "public_gap": ""})
        answer = service.solve_task(
            domain="inspection", task_ref="no-gap", question="target inspection",
            allow_external=True, provider="brave", max_attempts=2)
        self.assertEqual(answer["status"], "host_reported_failure")
        self.assertEqual(len(answer["research_attempts"]), 1)
        self.assertEqual(answer["research_attempts"][0]["host_feedback"], "failed")
        self.assertEqual(len(self.trials()), 1)

    def test_invalid_host_feedback_does_not_claim_success(self):
        service = WebResearchService(
            self.core, sources=self.sources,
            trusted_verifier=lambda **_: {"passed": "yes"})
        answer = service.solve_task(
            domain="inspection", task_ref="invalid-feedback",
            question="target inspection", provider="brave",
            allow_external=True, max_attempts=2)
        self.assertEqual(answer["status"], "host_verifier_unavailable")
        self.assertEqual(answer["research_attempts"][0]["host_feedback"],
                         "verifier_unavailable")
        self.assertFalse(self.trials()[0]["final_answer_verified"])

    def test_invalid_input_fails_before_network_and_handler_exists(self):
        with self.assertRaisesRegex(ValueError, "trusted host verifier"):
            self.run_task(allow_external=True, max_attempts=2)
        with self.assertRaisesRegex(ValueError, "Explicit web consent"):
            self.run_task(allow_external="yes")
        self.assertEqual(self.sources.call_count, 0)
        inbox = FakeInbox()
        register_web_research_handlers(inbox, self.service)
        self.assertIn("research_solve", inbox.commands)


if __name__ == "__main__":
    unittest.main()
