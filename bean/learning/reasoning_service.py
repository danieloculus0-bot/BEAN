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
from .judgment import choose_counsel
from .local_reasoner import LocalReasoner
from .transfer_gate import evaluate_transfer
from .active_hypothesis import discover, act
from .composition import CompositionLearner
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
    if provider_kind not in ("openai", "ollama", "openrouter", "local_llamacpp", "real_model", "synthetic_fixture"):
        raise ValueError("Unknown provider identity cannot earn evidence")
    return answer.strip(), model_id, provider_kind, provider_id


class NativeReasoningService:
    """Unified callable Core surface: generate, remember, evaluate, decide."""

    def __init__(self, path, *, model=None):
        self.path = Path(path)
        self.bank = ExperienceBank(self.path)
        self.skills = BEANReasoningSkills(self.bank)
        self.local = LocalReasoner(self.bank)
        self.compositions = CompositionLearner(self.bank)
        self.model = model
        self.closed = False

    def discover_analogy(self, *, domain, task_ref, source_ref,
                         probe_ids, observe, reward, budget=12,
                         method="disagreement", seed=0):
        """Generate numeric control hypotheses and seek distinguishing evidence.

        No source policy or expert candidate is supplied. The callbacks are
        actual resettable host environment interactions, not synthetic proof
        of general reasoning. SHA-chained evidence persists, including failures.
        """
        if self.closed:
            raise ValueError("Reasoning memory is closed")
        domain = _required(domain, "domain", 100).casefold()
        task_ref = _required(task_ref, "task_ref", 200)
        source_ref = _required(source_ref, "source_ref", 500)
        result = discover(
            probe_ids=probe_ids, observe=observe, reward=reward,
            budget=budget, method=method, seed=seed)
        entry = {
            "schema": "bean.adaptive_lab026.v1",
            "experiment": "bean.native.active_hypothesis.v1",
            "domain": domain, "task_ref": task_ref,
            "source_ref": source_ref, "decision": result,
            "outcome_origin": "host_observation_and_reward",
            "independently_authenticated": False,
        }
        receipt_id = sha256(canonical(entry)).hexdigest()
        tip = self.bank.record_trial(entry)
        return {**result, "receipt_id": receipt_id,
                "journal_tip": tip, "evidence_retained": True,
                "external_model_invoked": False}

    def revise_discovered_analogy(self, *, parent_receipt_id, domain, task_ref,
                                  source_ref, probe_ids, observe, reward,
                                  budget=12, method="disagreement", seed=0,
                                  min_gain=0.08):
        """Reevaluate a saved numeric rule using fresh matched host feedback.

        The new decision is separately journaled; the parent decision and
        negative observations remain intact. Host rewards are not verified.
        """
        from .active_hypothesis import _vector
        import math

        if self.closed:
            raise ValueError("Reasoning memory is closed")
        domain = _required(domain, "domain", 100).casefold()
        task_ref = _required(task_ref, "task_ref", 200)
        source_ref = _required(source_ref, "source_ref", 500)
        parent_receipt_id = _required(parent_receipt_id, "parent_receipt_id", 64)
        if (type(min_gain) not in (int, float) or not math.isfinite(min_gain)
                or min_gain < 0):
            raise ValueError("min_gain must be finite and nonnegative")

        trials = [event["data"] for event in self.bank.journal.events()
                  if event["kind"] == "trial" and event["data"].get(
                      "experiment") == "bean.native.active_hypothesis.v1"]
        by_receipt = {sha256(canonical(trial)).hexdigest(): trial
                      for trial in trials}
        if parent_receipt_id not in by_receipt:
            raise ValueError("Unknown previous hypothesis receipt")
        if by_receipt[parent_receipt_id]["domain"] != domain:
            raise ValueError("Revision domain differs from parent")

        # Treat every previously sampled probe in the ancestry as used
        # evidence: repeating it cannot count as fresh learning.
        used_probes, seen_receipts = set(), set()
        cursor = parent_receipt_id
        while cursor:
            if cursor in seen_receipts or cursor not in by_receipt:
                raise ValueError("Invalid hypothesis revision ancestry")
            seen_receipts.add(cursor)
            previous = by_receipt[cursor]["decision"]
            used_probes.update(row["probe_id"] for row in previous["records"])
            cursor = previous.get("parent_receipt_id")
        if (not isinstance(probe_ids, (tuple, list)) or
                any(not isinstance(pid, str) for pid in probe_ids) or
                set(probe_ids) & used_probes):
            raise ValueError("Revision requires unseen probe IDs")

        parent = by_receipt[parent_receipt_id]["decision"]
        dimensions = len(parent["records"][0]["sensors"])
        fresh = discover(probe_ids=probe_ids, observe=observe, reward=reward,
                         budget=budget, method=method, seed=seed)
        if any(len(row["sensors"]) != dimensions for row in fresh["records"]):
            raise ValueError("Sensor layout changed across revisions")

        prior = parent.get("selected_rule")
        prior_regret = None
        if prior is not None:
            loss = 0.0
            for row in fresh["records"]:
                sensors = _vector(row["sensors"], dimensions=dimensions)
                rewards = dict(row["rewards_by_action"])
                loss += max(rewards.values()) - rewards[act(prior, sensors)]
            prior_regret = loss / len(fresh["records"])
        advantage = (None if prior_regret is None
                     else prior_regret - fresh["best_loss_per_probe"])

        if fresh["selected_rule"] is not None and (
                prior is None or advantage > min_gain):
            selected = fresh["selected_rule"]
            change = "updated_from_fresh_feedback"
        elif prior is not None and prior_regret <= 0.12:
            selected = prior
            change = "retained_after_fresh_feedback"
        else:
            selected = None
            change = "abstained_insufficient_fresh_support"

        fresh.update({
            "parent_receipt_id": parent_receipt_id,
            "revision_decision": change,
            "prior_regret_per_probe": prior_regret,
            "fresh_advantage_per_probe": advantage,
            "minimum_change_advantage": float(min_gain),
            "previous_evidence_preserved": True,
            "independent_validation": False,
            "selected_rule": selected,
            "status": "provisional_rule" if selected is not None else "abstain",
            "failure_reason": (None if selected is not None
                               else "insufficient_evidence_or_model_mismatch"),
        })
        fresh.pop("evidence_sha256", None)
        fresh["evidence_sha256"] = sha256(json.dumps(
            fresh, sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode()).hexdigest()
        entry = {
            "schema": "bean.adaptive_lab026.v1",
            "experiment": "bean.native.active_hypothesis.v1",
            "domain": domain, "task_ref": task_ref, "source_ref": source_ref,
            "decision": fresh,
            "outcome_origin": "host_observation_and_reward",
            "independently_authenticated": False,
        }
        receipt_id = sha256(canonical(entry)).hexdigest()
        tip = self.bank.record_trial(entry)
        return {**fresh, "receipt_id": receipt_id, "journal_tip": tip,
                "evidence_retained": True, "external_model_invoked": False}

    def use_discovered_analogy(self, *, receipt_id, sensors):
        """Replay an empirically selected rule from the durable BEAN ledger."""
        if self.closed:
            raise ValueError("Reasoning memory is closed")
        candidates = [e["data"] for e in self.bank.journal.events()
                      if e["kind"] == "trial" and
                      e["data"].get("experiment") == "bean.native.active_hypothesis.v1"]
        for entry in reversed(candidates):
            if sha256(canonical(entry)).hexdigest() != receipt_id:
                continue
            stored = entry["decision"]
            if stored["status"] != "provisional_rule":
                return {"status": "abstain", "reason": "no_accepted_hypothesis"}
            from .active_hypothesis import _vector
            numbers = _vector(sensors)
            # Index validity alone is insufficient: a retained rule is tied
            # to the complete observed sensor layout, including unused channels.
            expected_dimensions = len(stored["records"][0]["sensors"])
            if len(numbers) != expected_dimensions:
                raise ValueError("Incompatible sensor layout")
            rule = stored["selected_rule"]
            if (rule["lhs"] is not None and rule["lhs"] >= len(numbers)) or (
                    rule["rhs"] is not None and rule["rhs"] >= len(numbers)):
                raise ValueError("Incompatible sensor layout")
            return {"status": "provisional_action",
                    "action": act(rule, numbers),
                    "hypothesis": rule, "receipt_id": receipt_id,
                    "independent_validation": False}
        raise ValueError("Unknown active hypothesis receipt")

    def test_analogy(self, *, domain, task_ref, source_ref, retained,
                     alternative, probe_ids, reward, margin=0.0):
        """Use local paired interventions to accept or reject a proposed transfer.

        Both candidates are caller-provided. Their outcomes are measured by
        an actual environment callback, retained in Core's SHA evidence bank.
        This does not generate abstractions or authenticate host feedback.
        """
        if self.closed:
            raise ValueError("Reasoning memory is closed")
        domain = _required(domain, "domain", 100).casefold()
        task_ref = _required(task_ref, "task_ref", 200)
        source_ref = _required(source_ref, "source_ref", 500)
        decision = evaluate_transfer(
            retained=retained, alternative=alternative,
            probe_ids=probe_ids, reward=reward, margin=margin)
        entry = {
            "schema": "bean.adaptive_lab026.v1",
            "experiment": "bean.native.selective_transfer.v1",
            "domain": domain, "task_ref": task_ref,
            "source_ref": source_ref,
            "decision": decision, "outcome_origin": "host_measured",
            "independent_verification": False,
        }
        receipt_id = sha256(canonical(entry)).hexdigest()
        tip = self.bank.record_trial(entry)
        return {**decision, "receipt_id": receipt_id,
                "journal_tip": tip, "lesson_retained": True,
                "model_invoked": False}

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

    def learn_local(self, *, domain, task_ref, examples, evidence_refs):
        """Generate/test/retain a symbolic rule locally, without model tokens."""
        return self.local.learn(domain=domain, task_ref=task_ref,
                                examples=examples, evidence_refs=evidence_refs)

    def compare_compositions(self, *, domain, task_ref, examples, evidence_refs):
        """Evaluate matched alternatives and retain reason-coded outcomes."""
        return self.compositions.compare(
            domain=domain, task_ref=task_ref,
            examples=examples, evidence_refs=evidence_refs)

    def propose_compositions(self, *, domain, task_ref, query):
        """Discover candidate combinations without assuming or retaining an answer."""
        return self.compositions.propose(
            domain=domain, task_ref=task_ref, query=query)

    def learn_composition(self, *, domain, task_ref, examples, evidence_refs):
        """Search combinations of retained rules and prove a unique development fit."""
        return self.compositions.learn(domain=domain, task_ref=task_ref,
                                       examples=examples, evidence_refs=evidence_refs)

    def reason_composed(self, *, domain, task_ref, query):
        """Apply a source-linked multi-rule program with bounded abstention."""
        return self.compositions.reason(domain=domain, task_ref=task_ref, query=query)

    def reason_local(self, *, domain, task_ref, query):
        """Local primitive first, then a discovered composition, no provider."""
        primitive = self.local.reason(domain=domain, task_ref=task_ref, question=query)
        if primitive["status"] == "locally_solved":
            return primitive
        composed = self.reason_composed(domain=domain, task_ref=task_ref, query=query)
        if composed["status"] == "locally_solved" or (
                composed["reason"] != "unsupported_composite_question"):
            return composed
        return primitive

    def reason_auto(self, *, domain, task_ref, query,
                    allow_provider=False, model=None):
        """BEAN first. A provider is used ONLY when the caller opts in.

        An unknown/ambiguous local result cannot secretly trigger cost.
        The existing reasoning selection and judgment rules remain intact.
        """
        if type(allow_provider) is not bool:
            raise ValueError("Explicit Boolean provider opt-in required")
        local = self.reason_local(domain=domain, task_ref=task_ref, query=query)
        if local["status"] == "locally_solved":
            return local
        selected_model = model if model is not None else self.model
        # A locally hosted llama.cpp engine has NO API token charges and NO
        # remote provider fallback. Use it after BEAN's symbolic learning
        # abstains, even when paid/cloud provider use is not authorized.
        if getattr(selected_model, "adapter_name", None) == "local_llamacpp":
            try:
                result = self.reason(
                    domain=domain, task_ref=task_ref, query=query,
                    model=selected_model)
            except RuntimeError:
                return {**local, "status": "local_model_unavailable",
                        "local_model_invoked": True,
                        "failed_inference_attempt_logged": True,
                        "external_provider_skipped": True,
                        "external_cost_usd": 0}
            return {**result, "local_attempt": local["reason"],
                    "local_model_invoked": True,
                    "external_provider_skipped": True,
                    "external_cost_usd": 0}
        if not allow_provider:
            return {**local, "external_provider_skipped": True}
        result = self.reason(
            domain=domain, task_ref=task_ref, query=query, model=model)
        return {**result, "local_attempt": local["reason"],
                "external_provider_skipped": False}

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
        selected_model = self._model(model)
        try:
            answer, model_id, provider_kind, provider_id = _model_response(
                selected_model, request, "")
        except Exception as exc:
            self._record_failure(
                purpose="model_authored_unverified_hypothesis",
                domain=domain, task_ref=task_ref, query=request,
                model=selected_model, exc=exc)
            raise
        receipt = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": "model_authored_unverified_hypothesis",
            "domain": domain, "task_ref": task_ref, "query": request,
            "answer": answer, "model_id": model_id, "provider_kind": provider_kind,
            "provider_response_id": provider_id, "source_refs": list(refs),
            "verified_outcome": False,
            "event_sequence": len(self.bank.journal.events()) + 1,
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
                   and x["data"].get("purpose") in ("selected_strategy_applied", "research_answer", "local_rule_applied", "local_cold_inference", "local_composition_applied")]
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
            # Store *which question* the correction belongs to. Otherwise
            # task-time lexical retrieval sees only a generic explanation and
            # can forget the newly learned lesson on a similar future prompt.
            # Preserve the original full question in the inference receipt;
            # carry only bounded context into the reusable lesson.
            question = _required(original.get("query"), "source question")
            if len(hypothesis) > 1800:
                raise ValueError("Correction hypothesis exceeds memory budget")
            contextual_hypothesis = (
                "Original question: " + question[:500] +
                "; proposed correction: " + hypothesis)
            saved = self.skills.reflect(
                domain=original["domain"], task_id=original["task_ref"],
                observed=actual, expected=expected,
                adjustment_hypothesis=contextual_hypothesis,
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
            "event_sequence": len(self.bank.journal.events()) + 1,
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

    def reason(self, *, domain, task_ref, query, model=None, candidates=None,
               stakes="normal", conflicting_evidence=False):
        """Use BEAN's *selected* memory then invoke exactly one actual model."""
        judgment = None
        if candidates is not None:
            judgment = self.judge(
                domain=domain, task_ref=task_ref, query=query,
                candidates=candidates, stakes=stakes,
                conflicting_evidence=conflicting_evidence)
            if judgment["decision"] != "explore":
                return {
                    "schema": "bean.native.reasoning.counsel_result.v1",
                    "answer": judgment["answer"], "decision": judgment,
                    "model_invoked": False, "verified_outcome": False,
                    "provider_kind": "none", "receipt_id": judgment["receipt_id"],
                }
        selected_model = self._model(model)
        try:
            packet = self.decide(domain=domain, task_ref=task_ref, query=query)
        except ValueError:
            if getattr(selected_model, "adapter_name", None) != "local_llamacpp":
                raise
            # A new BEAN domain has no measured strategy yet. Local language
            # inference may supply a *cold, unselected baseline* for later
            # assessment, but must never impersonate a measured winning arm.
            packet = {
                "schema": "bean.native.reasoning.local_cold_start.v1",
                "domain": _required(domain, "domain", 100).casefold(),
                "task_ref": _required(task_ref, "task_ref", 200),
                "selected_strategy": "cold", "lessons": [],
                "selection_trial_hash": None,
                "decision_source": "unselected_local_model_baseline",
                "model_invoked": False,
            }
        context = material_for(self.bank, packet["selected_strategy"],
                               packet["domain"], query=query)
        try:
            answer, model_id, provider_kind, provider_id = _model_response(
                selected_model, query, context)
        except Exception as exc:
            self._record_failure(
                purpose=("local_cold_inference" if
                         packet["decision_source"] == "unselected_local_model_baseline"
                         else "selected_strategy_applied"),
                domain=packet["domain"], task_ref=packet["task_ref"],
                query=query, model=selected_model, exc=exc)
            raise
        record = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": ("local_cold_inference" if
                        packet["decision_source"] == "unselected_local_model_baseline"
                        else "selected_strategy_applied"),
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
            "event_sequence": len(self.bank.journal.events()) + 1,
        }
        record["receipt_id"] = sha256(canonical(record)).hexdigest()
        tip = self.bank.record_inference(record)
        return {"schema": record["schema"], "answer": answer,
                "model_id": model_id, "provider_kind": provider_kind,
                "receipt_id": record["receipt_id"], "journal_tip": tip,
                "decision": packet, "verified_outcome": False,
                "judgment": judgment}

    def judge(self, *, domain, task_ref, query, candidates, stakes="normal",
              conflicting_evidence=False):
        """Arbitrate established answers without a provider or duplicate memory."""
        record = choose_counsel(
            domain=domain, task_ref=task_ref, query=query,
            candidates=candidates, stakes=stakes,
            conflicting_evidence=conflicting_evidence)
        record["event_sequence"] = len(self.bank.journal.events()) + 1
        record["receipt_id"] = sha256(canonical(record)).hexdigest()
        tip = self.bank.record_judgment(record)
        return {**record, "journal_tip": tip}

    def judgment_feedback(self, *, receipt_id, outcome, evidence_refs, note=None):
        """Retain host-reported successes and failures for future calibration."""
        receipt_id = _required(receipt_id, "receipt_id", 64)
        if len(receipt_id) != 64 or any(c not in "0123456789abcdef" for c in receipt_id):
            raise ValueError("A full judgment receipt hash is required")
        if outcome not in ("supported", "refuted", "inconclusive"):
            raise ValueError("Unsupported judgment outcome")
        if not isinstance(evidence_refs, (list, tuple)) or not 1 <= len(evidence_refs) <= 12:
            raise ValueError("Need 1..12 evidence reference identifiers")
        refs = [_required(ref, "outcome evidence reference", 500)
                for ref in evidence_refs]
        if note is not None:
            note = _required(note, "outcome note", 1800)
        originals = [row["data"] for row in self.bank.journal.events()
                     if row.get("kind") == "judgment"
                     and row["data"].get("receipt_id") == receipt_id]
        if len(originals) != 1:
            raise ValueError("Judgment receipt not found")
        original = originals[0]
        event = {
            "schema": "bean.judgment.feedback.v1",
            "receipt_id": receipt_id, "domain": original["domain"],
            "selected_source_ref": original["selected_source_ref"],
            "decision": original["decision"], "outcome": outcome,
            "evidence_refs": refs, "note": note,
            "outcome_origin": "host_reported",
            "independently_authenticated": False,
        }
        if any(row["kind"] == "judgment_feedback" and row["data"] == event
               for row in self.bank.journal.events()):
            return {**event, "new_feedback": False}
        tip = self.bank.record_judgment_feedback(event)
        return {**event, "new_feedback": True, "journal_tip": tip}

    def status(self):
        events = self.bank.journal.events()
        return {"schema": "bean.native.reasoning.status.v1",
                "engine": "BEANReasoningSkills",
                "storage": "owned_sha256_chain_sqlite",
                "stored_lessons": sum(x["kind"] == "lesson" for x in events),
                "native_symbolic_rules": sum(x["kind"] == "local_rule" for x in events),
                "native_composed_rules": sum(x["kind"] == "composed_rule" for x in events),
                "composition_comparisons": sum(
                    x["kind"] == "composition_comparison" for x in events),
                "native_symbolic_inferences": sum(
                    x["kind"] == "inference" and x["data"].get("provider_kind") == "native_local"
                    for x in events),
                "measured_trials": sum(x["kind"] == "trial" for x in events),
                "selected_strategies": sum(x["kind"] == "selection" for x in events),
                "inference_receipts": sum(x["kind"] == "inference" for x in events),
                "failed_inference_attempts": sum(
                    x["kind"] == "inference" and
                    x["data"].get("status") == "failed" for x in events),
                "feedback_receipts": sum(x["kind"] == "feedback" for x in events),
                "research_evidence_packets": sum(x["kind"] == "research" for x in events),
                "judgment_receipts": sum(x["kind"] == "judgment" for x in events),
                "judgment_outcomes": sum(x["kind"] == "judgment_feedback" for x in events),
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
    inbox.register("reasoning_learn_local", lambda m, _: service.learn_local(**m.args))
    inbox.register("reasoning_compare_compositions", lambda m, _: service.compare_compositions(**m.args))
    inbox.register("reasoning_propose_compositions", lambda m, _: service.propose_compositions(**m.args))
    inbox.register("reasoning_learn_composition", lambda m, _: service.learn_composition(**m.args))
    inbox.register("reasoning_composed", lambda m, _: service.reason_composed(**m.args))
    inbox.register("reasoning_local", lambda m, _: service.reason_local(**m.args))
    inbox.register("reasoning_auto", lambda m, _: service.reason_auto(**m.args))
    inbox.register("reasoning_recall", lambda m, _: service.recall(**m.args))
    inbox.register("reasoning_reflect", lambda m, _: service.reflect(**m.args))
    inbox.register("reasoning_skill", lambda m, _: service.retain_skill(**m.args))
    inbox.register("reasoning_instruction", lambda m, _: service.propose_instruction(**m.args))
    inbox.register("reasoning_generate", lambda m, _: service.generate(**m.args))
    inbox.register("reasoning_compare", lambda m, _: service.choose_from_outcomes(**m.args))
    inbox.register("reasoning_decide", lambda m, _: service.decide(**m.args))
    inbox.register("reasoning_reason", lambda m, _: service.reason(**m.args))
    inbox.register("reasoning_feedback", lambda m, _: service.feedback(**m.args))
    inbox.register("reasoning_judge", lambda m, _: service.judge(**m.args))
    inbox.register("reasoning_judgment_feedback", lambda m, _: service.judgment_feedback(**m.args))
    return inbox
