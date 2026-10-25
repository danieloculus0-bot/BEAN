"""Real external BEAN AI Bridge evidence adapter.

The Bridge is a separate repository, not a built-in BEAN Core subsystem.
Its caller-provided verifier is not automatically an independent fact source.
"""
from __future__ import annotations
from dataclasses import asdict
import importlib.util


def bridge_contract():
    if importlib.util.find_spec("ezbean") is None:
        return {"bridge_available": False, "real_core_interoperability": False,
                "reason": "BEAN AI Bridge checkout not installed"}
    from ezbean.knowledge_gate import DefinitionLibrary
    from ezbean.learning_loop import EvidenceLearningLoop, SourceObservation
    return {
        "bridge_available": True,
        "real_core_interoperability": True,
        "api": [DefinitionLibrary.__module__, EvidenceLearningLoop.__module__,
                SourceObservation.__module__],
        "outcome_verified": False,
        "note": "API import test; behavior validated only by an executed Bridge trial",
    }


def audit_sources(*, db_path, concept, as_of, observations, verifier, provider):
    """Call the actual Bridge EvidenceLearningLoop with typed source records."""
    if not bridge_contract()["bridge_available"]:
        raise RuntimeError("Actual Bridge sources unavailable")
    from ezbean.knowledge_gate import DefinitionLibrary
    from ezbean.learning_loop import EvidenceLearningLoop, SourceObservation
    if not all(isinstance(x, SourceObservation) for x in observations):
        raise TypeError("Bridge evidence must be typed SourceObservation")
    class Investigator:
        def investigate(self, name, question):
            return observations
    library = DefinitionLibrary(db_path)
    try:
        runner = EvidenceLearningLoop(library, investigator=Investigator(),
                                      verifier=verifier)
        outcome = runner.process(provider, concept, as_of, refresh=True)
        return {
            "schema": "bean.adaptive_bridge_lab026.v1",
            "outcome": asdict(outcome),
            "history_count": len(runner.history()),
            "evidence_summary": runner.compile_evidence(),
            "independent_fact_authentication": False,
        }
    finally:
        library.close()
