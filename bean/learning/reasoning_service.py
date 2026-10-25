"""BEAN Core's owned reasoning-learning loop and optional provider boundary.

No separate memory engine. The hash-chained ExperienceBank holds source-linked
lessons, measured policy selections, task-time decisions, and actual inference
receipts. Providers generate text only. BEAN controls selection and evidence.
Host-reported rewards remain unverified until independently judged.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

from .experimental import ExperienceBank, TrialCase, material_for
from .native_skills import BEANReasoningSkills
from bean.optimization.autodev import canonical


def _required(value, name, maximum=3000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(name + " must be nonempty bounded text")
    return value.strip()


def _model_response(model, query, context):
    """Adapt real generic model text or existing BEAN provider response."""
    if model is None or not callable(getattr(model, "complete", None)):
        raise ValueError("Actual configured reasoning model required; no fake fallback")
    reply = model.complete(query, context)
    if isinstance(reply, dict):
        if reply.get("ok") is not True or not isinstance(reply.get("raw_text"), str):
            raise RuntimeError("Reasoning provider unavailable or produced invalid output")
        answer = reply["raw_text"]
        model_id = reply.get("model_name") or getattr(model, "model_name", None)
        provider_kind = reply.get("adapter_name") or getattr(model, "adapter_name", None)
        provider_id = reply.get("provider_response_id")
    elif isinstance(reply, str):
        answer = reply
        model_id = getattr(model, "model_id", None)
        provider_kind = getattr(model, "provider_kind", None)
        provider_id = None
    else:
        raise ValueError("Provider must return actual inference text")
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 12000:
        raise ValueError("Provider returned empty or oversized inference")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("Unidentified model cannot earn a reasoning receipt")
    if provider_kind not in ("openai", "ollama", "openrouter", "real_model", "synthetic_fixture"):
        raise ValueError("Unknown provider identity cannot earn evidence")
    return answer.strip(), model_id, provider_kind, provider_id


class NativeReasoningService:
    """Unified callable Core surface: generate, remember, evaluate, decide."""

    def __init__(self, path, *, model=None):
        self.path = Path(path)
        self.bank = ExperienceBank(self.path)
        self.skills = BEANReasoningSkills(self.bank)
        self.model = model
        self.closed = False

    def _model(self, model=None):
        selected = model if model is not None else self.model
        if selected is None:
            raise ValueError("No reasoning model configured; model calls are not simulated")
        return selected

    def reflect(self, *, domain, task_id, observed, expected,
                adjustment_hypothesis, evidence_refs):
        return self.skills.reflect(
            domain=domain, task_id=task_id, observed=observed,
            expected=expected, adjustment_hypothesis=adjustment_hypothesis,
            evidence_refs=evidence_refs)

    def retain_skill(self, *, domain, name, steps, passed, evidence_refs):
        return self.skills.retain_skill(
            domain=domain, name=name, steps=steps, passed=passed,
            evidence_refs=evidence_refs)

    def propose_instruction(self, *, domain, instruction, evidence_refs):
        return self.skills.propose_instruction(
            domain=domain, instruction=instruction, evidence_refs=evidence_refs)

    def recall(self, *, domain, query, strategy=None, limit=3):
        return self.skills.recall(domain=domain, query=query,
                                  strategy=strategy, limit=limit)

    def generate(self, *, domain, task_ref, examples, evidence_refs, model=None):
        """Ask an actual reasoning model to formulate a candidate lesson.

        The examples are all development data supplied by the host. The
        generated lesson is UNVERIFIED until BEAN's measured selection.
        """
        domain = _required(domain, "domain", 100).casefold()
        task_ref = _required(task_ref, "task_ref", 200)
        if (not isinstance(examples, list) or not 2 <= len(examples) <= 8
                or any(not isinstance(item, dict)
                       or set(item) != {"question", "answer"}
                       for item in examples)):
            raise ValueError("Need 2..8 development question/answer examples")
        bounded = [{
            "question": _required(item["question"], "question", 1000),
            "answer": _required(item["answer"], "answer", 1000)
        } for item in examples]
        request = ("Induce a reusable procedure for domain " + domain +
                   " from ONLY these observed development examples. "
                   "Respond with a concise general rule, not example answers. "
                   "Do not assume this rule is verified:\n" +
                   json.dumps(bounded, separators=(",", ":"), ensure_ascii=False))
        if not isinstance(evidence_refs, (tuple, list)) or not evidence_refs:
            raise ValueError("Development evidence references required")
        refs = tuple(_required(ref, "development evidence reference", 500)
                     for ref in evidence_refs)
        try:
            answer, model_id, provider_kind, provider_id = _model_response(
                self._model(model), request, "")
        except Exception as exc:
            self._record_failure(
                purpose="model_authored_unverified_hypothesis",
                domain=domain, task_ref=task_ref, query=request,
                model=model, exc=exc)
            raise
        receipt = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": "model_authored_unverified_hypothesis",
            "domain": domain, "task_ref": task_ref, "query": request,
            "answer": answer, "model_id": model_id, "provider_kind": provider_kind,
            "provider_response_id": provider_id, "source_refs": list(refs),
            "verified_outcome": False,
        }
        receipt_id = sha256(canonical(receipt)).hexdigest()
        receipt["receipt_id"] = receipt_id
        tip = self.bank.record_inference(receipt)
        lesson = self.skills.propose_instruction(
            domain=domain, instruction=answer,
            evidence_refs=tuple(refs) + ("inference:" + receipt_id,))
        return {"receipt_id": receipt_id, "journal_tip": tip,
                "candidate": lesson, "rule": answer,
                "model_id": model_id, "unverified": True}

    def feedback(self, *, receipt_id, expected, evidence_refs,
                 adjustment_hypothesis=None):
        """Persist success or error and a source-linked correction when needed.

        Every scored outcome is host reported, never self-certified as truth.
        Identical repeated feedback is idempotent, while conflicting evidence
        can be recorded separately without altering historical reports.
        """
        receipt_id = _required(receipt_id, "receipt_id", 64)
        if len(receipt_id) != 64 or any(x not in "0123456789abcdef" for x in receipt_id):
            raise ValueError("A full SHA-256 inference receipt ID is required")
        expected = _required(expected, "expected")
        if (not isinstance(evidence_refs, (tuple, list))
                or not 1 <= len(evidence_refs) <= 15):
            raise ValueError("1..15 feedback source references are required")
        refs = tuple(_required(x, "feedback evidence reference", 500)
                     for x in evidence_refs)
        matched = [x["data"] for x in self.bank.journal.events()
                   if x["kind"] == "inference"
                   and x["data"].get("receipt_id") == receipt_id
                   and x["data"].get("purpose") == "selected_strategy_applied"]
        if len(matched) != 1:
            raise ValueError("Exactly one completed BEAN reasoning receipt required")
        original = matched[0]
        actual = original["answer"]
        correct = actual == expected
        hypothesis = None if correct else _required(
            adjustment_hypothesis, "adjustment_hypothesis")
        event = {
            "schema": "bean.native.reasoning.feedback.v1",
            "receipt_id": receipt_id,
            "domain": original["domain"],
            "task_ref": original["task_ref"],
            "selected_strategy": original["selected_strategy"],
            "matched": correct, "observed": actual, "expected": expected,
            "adjustment_hypothesis": hypothesis,
            "source_refs": list(refs),
            "outcome_origin": "host_reported",
            "independently_authenticated": False,
        }
        same = [e["data"] for e in self.bank.journal.events()
                if e["kind"] == "feedback" and e["data"] == event]
        if same:
            return {"schema": event["schema"], "receipt_id": receipt_id,
                    "matched": correct, "new_feedback": False,
                    "correction_added": False}
        saved = None
        if not correct:
            saved = self.skills.reflect(
                domain=original["domain"], task_id=original["task_ref"],
                observed=actual, expected=expected,
                adjustment_hypothesis=hypothesis,
                evidence_refs=refs + ("inference:" + receipt_id,))
        event_tip = self.bank.record_feedback(event)
        return {"schema": event["schema"], "receipt_id": receipt_id,
                "matched": correct, "new_feedback": True,
                "journal_tip": event_tip,
                "correction_added": bool(saved and saved["new"]),
                "lesson_id": saved["lesson_id"] if saved else None,
                "outcome_origin": "host_reported",
                "selected_strategy": original["selected_strategy"]}

    def _record_failure(self, *, purpose, domain, task_ref, query, model, exc):
        """Retain a model outage, with no fabricated answer or secret error text."""
        configured = model or self.model
        model_id = (getattr(configured, "model_id", None)
                    or getattr(configured, "model_name", None)
                    or "not_configured")
        entry = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": purpose, "status": "failed",
            "domain": domain, "task_ref": task_ref,
            "question_sha256": sha256(query.encode()).hexdigest(),
            "answer": "", "model_id": str(model_id),
            "exception_class": type(exc).__name__,
            "verified_outcome": False,
        }
        entry["receipt_id"] = sha256(canonical(entry)).hexdigest()
        self.bank.record_inference(entry)

    def choose_from_outcomes(self, *, domain, rows, evaluator_id, dataset_id,
                             minimum_gain=1):
        """Select from exactly matched external control arms, not a fabricated grade."""
        return self.skills.select_strategy(
            domain=domain, rows=rows, evaluator_id=evaluator_id,
            dataset_id=dataset_id, minimum_gain=minimum_gain)

    def evaluate_and_select(self, *, domain, cases, model, judge, batched=False,
                            replicates=1, minimum_gain=1):
        return self.skills.evaluate_and_select(
            domain=domain, cases=cases, model=model, judge=judge,
            batched=batched, replicates=replicates, minimum_gain=minimum_gain)

    def evaluate_holdout(self, *, domain, cases, model, judge, batched=False,
                         replicates=1):
        return self.skills.evaluate_holdout(
            domain=domain, cases=cases, model=model, judge=judge,
            batched=batched, replicates=replicates)

    def decide(self, *, domain, task_ref, query):
        """Real BEAN-selected, source-linked lesson packet, without a model call."""
        return self.skills.decide(domain=domain, task_ref=task_ref, query=query)

    def reason(self, *, domain, task_ref, query, model=None):
        """Use BEAN's *selected* memory then invoke exactly one actual model."""
        packet = self.decide(domain=domain, task_ref=task_ref, query=query)
        context = material_for(self.bank, packet["selected_strategy"],
                               packet["domain"], query=query)
        try:
            answer, model_id, provider_kind, provider_id = _model_response(
                self._model(model), query, context)
        except Exception as exc:
            self._record_failure(
                purpose="selected_strategy_applied",
                domain=packet["domain"], task_ref=packet["task_ref"],
                query=query, model=model, exc=exc)
            raise
        record = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": "selected_strategy_applied",
            "domain": packet["domain"], "task_ref": packet["task_ref"],
            "query": query, "answer": answer, "model_id": model_id,
            "provider_kind": provider_kind,
            "provider_response_id": provider_id,
            "source_refs": [r for item in packet["lessons"]
                            for r in item["evidence_refs"]],
            "selected_lesson_ids": [x["lesson_id"] for x in packet["lessons"]],
            "selection_trial_hash": packet["selection_trial_hash"],
            "selected_strategy": packet["selected_strategy"],
            "context_sha256": sha256(context.encode()).hexdigest(),
            "verified_outcome": False,
        }
        record["receipt_id"] = sha256(canonical(record)).hexdigest()
        tip = self.bank.record_inference(record)
        return {"schema": record["schema"], "answer": answer,
                "model_id": model_id, "provider_kind": provider_kind,
                "receipt_id": record["receipt_id"], "journal_tip": tip,
                "decision": packet, "verified_outcome": False}

    def status(self):
        events = self.bank.journal.events()
        return {"schema": "bean.native.reasoning.status.v1",
                "engine": "BEANReasoningSkills",
                "storage": "owned_sha256_chain_sqlite",
                "stored_lessons": sum(x["kind"] == "lesson" for x in events),
                "measured_trials": sum(x["kind"] == "trial" for x in events),
                "selected_strategies": sum(x["kind"] == "selection" for x in events),
                "inference_receipts": sum(x["kind"] == "inference" for x in events),
                "failed_inference_attempts": sum(
                    x["kind"] == "inference" and
                    x["data"].get("status") == "failed" for x in events),
                "feedback_receipts": sum(x["kind"] == "feedback" for x in events),
                "model_configured": self.model is not None,
                "host_truth_authenticated": False,
                "autonomous_general_learning_proven": False,
                "hosted_connector_integrated": False}

    def close(self):
        if not self.closed:
            self.bank.close()
            self.closed = True


def register_native_reasoning_handlers(inbox, service):
    """Install BEAN-owned local commands in the *existing* runtime inbox."""
    inbox.register("reasoning_status", lambda m, _: service.status())
    inbox.register("reasoning_recall", lambda m, _: service.recall(**m.args))
    inbox.register("reasoning_reflect", lambda m, _: service.reflect(**m.args))
    inbox.register("reasoning_skill", lambda m, _: service.retain_skill(**m.args))
    inbox.register("reasoning_instruction", lambda m, _: service.propose_instruction(**m.args))
    inbox.register("reasoning_generate", lambda m, _: service.generate(**m.args))
    inbox.register("reasoning_compare", lambda m, _: service.choose_from_outcomes(**m.args))
    inbox.register("reasoning_decide", lambda m, _: service.decide(**m.args))
    inbox.register("reasoning_reason", lambda m, _: service.reason(**m.args))
    inbox.register("reasoning_feedback", lambda m, _: service.feedback(**m.args))
    return inbox
