"""Join BEAN Core reasoning attempts to real BEAN AI Bridge source investigations.

One reasoning owner: NativeReasoningService's existing SHA-chained ExperienceBank.
One external evidence authority: ezbean.learning_loop.EvidenceLearningLoop,
running in the existing Bridge DefinitionLibrary database.

Bridge's *host-supplied* verifier remains accountable for source authenticity.
Only two distinct newly checked origins agreeing on a value can turn a
specific previously journaled Core model answer into feedback. Absent or
contradictory evidence remains open; no self-grading or automatic reward.
"""
from __future__ import annotations

import json
from pathlib import Path

from .bridge import audit_sources
from .reasoning_service import NativeReasoningService


class _CapturedReasoningProposal:
    """Present a previously produced Core answer to Bridge's actual OutputGate.

    The model does not see verified definitions. We use Bridge's source-gate
    only to assess the specific answer BEAN actually returned, not to ask an
    external provider to generate a new or replacement answer.
    """
    def __init__(self, answer):
        self.answer = answer

    def complete(self, snapshot):
        known = snapshot.get("verified_definition")
        # Include a definition ID only when the *model's preexisting answer*
        # agrees; never rewrite the answer using the knowledge library.
        refs = ([known["definition_id"]]
                if known is not None and known.get("value") == self.answer
                else [])
        return {"message": {"content": json.dumps(
            {"concept": snapshot["requested_concept"], "decision": "answer",
             "value": self.answer, "definition_ids": refs},
            separators=(",", ":"), ensure_ascii=False)}}


class BridgeReasoningLoop:
    """A single observed Core answer -> Bridge evidence -> Core feedback pass."""

    def __init__(self, service: NativeReasoningService, bridge_db,
                 *, verifier):
        if not isinstance(service, NativeReasoningService):
            raise TypeError("Actual BEAN-owned NativeReasoningService required")
        if not callable(getattr(verifier, "check", None)):
            raise TypeError("An actual host source verifier is required")
        self.service = service
        self.bridge_db = Path(bridge_db)
        self.verifier = verifier

    def attempt(self, *, domain, task_ref, query, concept, as_of,
                observations, adjustment_hypothesis=None):
        """Use a real model, then evaluate its *actual answer* against Bridge.

        The observations are ezbean SourceObservation instances. Bridge itself
        verifies source origins, records rejected claims and owns its versioned
        library; no caller-supplied fake grade can skip this process.
        """
        if not isinstance(concept, str) or not 1 <= len(concept.strip()) <= 100:
            raise ValueError("Bounded Bridge concept required")
        if not isinstance(observations, (list, tuple)) or not 1 <= len(observations) <= 8:
            raise ValueError("Need 1..8 independently checkable observations")
        # A selected BEAN policy must already exist. Provider errors are
        # journaled by NativeReasoningService and are never called successes.
        inference = self.service.reason(
            domain=domain, task_ref=task_ref, query=query)
        bridge = audit_sources(
            db_path=self.bridge_db, concept=concept.strip(), as_of=as_of,
            observations=observations, verifier=self.verifier,
            provider=_CapturedReasoningProposal(inference["answer"]))
        outcome = bridge["outcome"]
        status = outcome["investigation_status"]
        new_evidence = (
            outcome["result_status"] == "answerable"
            and isinstance(outcome.get("system_answer"), str)
            and outcome["system_answer"].strip()
            and status in ("committed_verified_revision", "corroborated_no_revision")
            and outcome["confirmed_sources"] >= 2
            and outcome["distinct_origins"] >= 2
            and len(outcome.get("evidence_refs") or []) >= 2
            and bool(outcome.get("definition_id"))
        )
        result = {
            "schema": "bean.bridge_core.reasoning_feedback.v1",
            "receipt_id": inference["receipt_id"],
            "model_id": inference["model_id"],
            "bridge_cycle_id": outcome["cycle_id"],
            "bridge_concept": outcome["concept"],
            "bridge_status": status,
            "bridge_definition_id": outcome.get("definition_id"),
            "source_refs": list(outcome["evidence_refs"]),
            "bridge_evidence_origin": "host_verifier_attested",
            "feedback_applied": False,
            "reasoning_answer": inference["answer"],
            "source_agreement": bool(new_evidence),
        }
        if not new_evidence:
            result["reason"] = "evidence_missing_incomplete_or_contradictory"
            return result

        # Stable source refs make repeating identical evidence idempotent.
        expected = outcome["system_answer"]
        sources = ["bridge_definition:" + outcome["definition_id"]]
        sources.extend("bridge_source:" + ref for ref in outcome["evidence_refs"])
        if len(sources) > 15:
            raise ValueError("Exceeded the evidence source receipt budget")
        hypothesis = adjustment_hypothesis
        if hypothesis is None and expected != inference["answer"]:
            # Scoped *correction*, not a model-generated generalized law.
            hypothesis = ("For " + concept.strip() +
                          ", consult the cited Bridge evidence; its observed "
                          "value is " + expected)
        feedback = self.service.feedback(
            receipt_id=inference["receipt_id"], expected=expected,
            adjustment_hypothesis=hypothesis, evidence_refs=sources)
        result.update({
            "feedback_applied": True,
            "matched": feedback["matched"],
            "correction_added": feedback["correction_added"],
            "learned_lesson_id": feedback.get("lesson_id"),
            "feedback_journal_tip": feedback.get("journal_tip"),
            "outcome_origin": "host_verifier_attested_not_independent_truth",
        })
        return result


def register_bridge_feedback_handler(inbox, loop):
    """Optional existing-inbox extension with a host-provided verifier.

    The host must instantiate BridgeReasoningLoop explicitly. BEAN's runtime
    cannot authenticate evidence from arbitrary JSON claims alone.
    """
    if not isinstance(loop, BridgeReasoningLoop):
        raise TypeError("Concrete BridgeReasoningLoop required")
    inbox.register("reasoning_bridge_experiment", lambda m, _: loop.attempt(**m.args))
    return inbox
