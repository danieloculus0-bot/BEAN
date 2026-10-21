"""Execute the REAL BEAN AI Bridge evidence loop from separate checkout.

These are synthetic, independently checked test records, not new findings
about the world. It also tests contradiction resistance after restart.
"""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from bean.learning.bridge import audit_sources,bridge_contract
try:
    from ezbean.knowledge_gate import DefinitionLibrary
    from ezbean.learning_loop import SourceObservation
except ModuleNotFoundError as exc:
    if exc.name != "ezbean":
        raise
    DefinitionLibrary = None
    SourceObservation = None


STAMP="2026-10-20T20:00:00Z"


class WrongCandidate:
    def complete(self, payload):
        return {"message":{"content":json.dumps({
            "concept":payload["requested_concept"],"decision":"answer",
            "value":"INVENTED","definition_ids":[]})}}


class AuthenticatingFixtureVerifier:
    """Fixed fixture oracle, NOT a real-world source authentication layer."""
    def check(self, concept, source):
        return source.value=="42" and source.ref.startswith("fixture:")


@unittest.skipUnless(
    DefinitionLibrary is not None,
    "BEAN AI Bridge is an external checkout; tested in dedicated Lab026 CI",
)
class BridgeViabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"bridge_definitions.sqlite"

    def test_source_dependency_is_real_import(self):
        status=bridge_contract()
        self.assertTrue(status["bridge_available"])
        self.assertTrue(status["real_core_interoperability"])
        self.assertIn("ezbean.learning_loop",status["api"])
        self.assertFalse(status["outcome_verified"])

    def test_bounded_evidence_loop_refutes_wrong_model_and_survives_restart(self):
        sources=[SourceObservation("fixture:1","lab_A","42"),
                 SourceObservation("fixture:2","lab_B","42")]
        result=audit_sources(db_path=self.path,concept="lab026_fact",
            as_of=STAMP,observations=sources,
            verifier=AuthenticatingFixtureVerifier(),provider=WrongCandidate())
        self.assertEqual(result["outcome"]["system_answer"],"42")
        self.assertEqual(result["outcome"]["investigation_status"],
                         "committed_verified_revision")
        self.assertFalse(result["outcome"]["model_accepted"])
        self.assertEqual(result["outcome"]["distinct_origins"],2)
        self.assertFalse(result["independent_fact_authentication"])
        store=DefinitionLibrary(self.path)
        try:
            definition,reason=store.lookup("lab026_fact",STAMP)
            self.assertEqual(definition.value,"42")
            self.assertEqual(reason,"current_verified")
        finally:
            store.close()

    def test_one_origin_does_not_become_knowledge(self):
        result=audit_sources(db_path=self.path,concept="lab026_unknown",
          as_of=STAMP,observations=[
              SourceObservation("fixture:one","single_origin","42")],
          verifier=AuthenticatingFixtureVerifier(),provider=WrongCandidate())
        self.assertEqual(result["outcome"]["result_status"],"unresolved")
        self.assertIsNone(result["outcome"]["system_answer"])

    def test_conflicting_sources_remain_inconclusive(self):
        class Both:
            def check(self, concept, observation):return True
        result=audit_sources(db_path=self.path,concept="lab026_conflict",
          as_of=STAMP,observations=[
              SourceObservation("fixture:A","sourceA","42"),
              SourceObservation("fixture:B","sourceB","43")],
          verifier=Both(),provider=WrongCandidate())
        self.assertEqual(result["outcome"]["investigation_status"],
                         "conflicting_verified_evidence")
        self.assertIsNone(result["outcome"]["system_answer"])


if __name__=="__main__":
    unittest.main()
