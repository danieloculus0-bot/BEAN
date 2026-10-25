"""BEAN-native reasoning skills. Reuses Lab026's existing evidence journal and selector.

Peer-inspired algorithms are implemented locally, without peer agent runtimes.
Host-reported observations are not automatically independently verified.
"""
from __future__ import annotations
from hashlib import sha256
import re
from .experimental import ExperienceBank, Lesson, task_lesson_matches
from .brain_port import choose_from_outcomes, brain_decision, connector_presentation_packet

SKILLS = ("reflection", "skill", "prompt")
SCHEMA = "bean.native_reasoning_skills.v1"
TOKENS = re.compile(r"[a-z0-9]+")


def _text(value, label, maximum=2500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(label + " must be nonempty bounded text")
    return value.strip()


def _evidence(refs):
    if not isinstance(refs, (list, tuple)) or not 1 <= len(refs) <= 16:
        raise ValueError("Need 1..16 evidence references")
    return tuple(_text(ref, "evidence reference", 500) for ref in refs)


def _words(text):
    return set(TOKENS.findall(text.casefold()))


class BEANReasoningSkills:
    """Recall, reflect, reuse and improve by measured selection. No I/O or LLM."""

    def __init__(self, bank: ExperienceBank):
        if not isinstance(bank, ExperienceBank):
            raise TypeError("Existing BEAN ExperienceBank required")
        self.bank = bank

    def _store(self, strategy, domain, content, evidence_refs, outcome):
        if strategy not in SKILLS:
            raise ValueError("Unknown BEAN skill type")
        domain = _text(domain, "domain", 100).casefold()
        content = _text(content, "content", 6500)
        refs = _evidence(evidence_refs)
        outcome = _text(outcome, "outcome", 200)
        payload = "\x1f".join((strategy, domain, content, outcome, *refs))
        identity = "bean.lesson." + sha256(payload.encode()).hexdigest()[:32]
        old = next((x for x in self.bank.lessons() if x.lesson_id == identity), None)
        if old:
            if (old.strategy, old.domain, old.text, old.evidence_refs,
                    old.observed_outcome) != (strategy, domain, content, refs, outcome):
                raise ValueError("Lesson hash collision")
            return {"lesson_id": identity, "new": False}
        self.bank.add(Lesson(identity, strategy, domain, content, refs, outcome))
        return {"lesson_id": identity, "new": True}

    def recall(self, *, domain, query, strategy=None, limit=3):
        """Task-relevant, same-domain, deterministic retrieval with exact evidence."""
        domain = _text(domain, "domain", 100).casefold()
        query = _text(query, "query")
        if strategy is not None and strategy not in SKILLS:
            raise ValueError("Unknown strategy")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("Invalid recall limit")
        strategies = (strategy,) if strategy else SKILLS
        ranked = []
        for arm in strategies:
            ranked.extend(task_lesson_matches(
                self.bank, strategy=arm, domain=domain, query=query, limit=limit))
        # Deterministic tie resolution, retaining the same source-linked
        # memory ranking whether BEAN or a matched trial consumes the lesson.
        ranked.sort(key=lambda result: (-result[0], result[1].lesson_id))
        return [{
            "lesson_id": item.lesson_id, "strategy": item.strategy,
            "domain": item.domain, "text": item.text,
            "evidence_refs": list(item.evidence_refs),
            "observed_outcome": item.observed_outcome,
            "matched_terms": score, "ranking": "domain_lexical_not_semantic_proof",
        } for score, item in ranked[:limit]]

    def reflect(self, *, domain, task_id, observed, expected,
                adjustment_hypothesis, evidence_refs):
        """Preserve a mistake and an explicit, unverified correction hypothesis."""
        task = _text(task_id, "task", 200)
        observed = _text(observed, "observed")
        expected = _text(expected, "expected")
        hypothesis = _text(adjustment_hypothesis, "hypothesis")
        if observed == expected:
            raise ValueError("No discrepancy to reflect upon")
        content = (f"Task {task}; observed: {observed}; expected: {expected}; "
                   f"unverified adjustment hypothesis: {hypothesis}")
        return self._store("reflection", domain, content, evidence_refs,
                           "host_reported_mismatch_not_verified")

    def retain_skill(self, *, domain, name, steps, passed, evidence_refs):
        """Store a successful reported procedure. It is not executed."""
        if passed is not True:
            raise ValueError("Skill needs a host-reported successful trial")
        name = _text(name, "name", 160)
        if not isinstance(steps, (list, tuple)) or not 1 <= len(steps) <= 12:
            raise ValueError("Need 1..12 reusable skill steps")
        content = "Procedure " + name + ":\n" + "\n".join(
            f"{i}. {_text(step, 'step', 500)}" for i, step in enumerate(steps, 1))
        return self._store("skill", domain, content, evidence_refs,
                           "host_reported_success_not_verified")

    def propose_instruction(self, *, domain, instruction, evidence_refs):
        """Store a candidate prompt. Improvements require paired evaluation."""
        content = "Instruction candidate: " + _text(instruction, "instruction", 3500)
        return self._store("prompt", domain, content, evidence_refs,
                           "unevaluated_instruction_candidate")

    def evaluate_and_select(self, *, domain, cases, model, judge, replicates=1,
                            minimum_gain=1):
        """Run actual paired model trials; reuse Lab026's independent selector.

        Synthetic providers remain synthetic. The judge owns the task answers;
        no learned-weight or causal-generalization claim follows from selection.
        """
        from .experimental import run_paired_trial
        from .strategy_selection import choose_strategy
        domain = _text(domain, "domain", 100).casefold()
        cases = list(cases)
        if len(cases) < 2 or any(case.domain != domain for case in cases):
            raise ValueError("Need >=2 selection tasks from the same domain")
        receipt = run_paired_trial(
            bank=self.bank, cases=cases, model=model, judge=judge,
            replicates=replicates, task_aware=True)
        selection = choose_strategy(
            self.bank, receipt, domain, minimum_gain=minimum_gain)
        return {"trial": receipt, "selection": selection}

    def evaluate_holdout(self, *, domain, cases, model, judge, replicates=1):
        """Evaluate frozen chosen strategy on disjoint IDs, without reselection.

        This does NOT certify that source questions were truly hidden.
        Do not use this outcome to change the already selected strategy.
        """
        from .experimental import run_paired_trial
        domain = _text(domain, "domain", 100).casefold()
        cases = list(cases)
        if len(cases) < 2 or any(case.domain != domain for case in cases):
            raise ValueError("Need >=2 same-domain holdout tasks")
        # Ensure a measured selection already exists.
        self.bank.selected_arm(domain)
        tested = {
            row.get("task_id")
            for event in self.bank.journal.events()
            if event.get("kind") == "trial"
            for row in event["data"].get("records", [])
        }
        if any(case.task_id in tested for case in cases):
            raise ValueError("Holdout task IDs overlap previous measured trials")
        receipt = run_paired_trial(
            bank=self.bank, cases=cases, model=model, judge=judge,
            arms=("cold", "placebo", "adaptive"), replicates=replicates)
        return {"trial": receipt, "scope": "post_selection_holdout_no_policy_change"}

    def select_strategy(self, *, domain, rows, evaluator_id, dataset_id,
                        minimum_gain=1):
        """Reuse BEAN's existing controlled Lab026 candidate selector."""
        return choose_from_outcomes(
            self.bank, domain=_text(domain, "domain", 100).casefold(),
            rows=rows, evaluator_id=evaluator_id, dataset_id=dataset_id,
            minimum_gain=minimum_gain)

    def decide(self, *, domain, task_ref, query):
        """Use selected journal policy; substitute task-relevant source lessons."""
        domain = _text(domain, "domain", 100).casefold()
        task_ref = _text(task_ref, "task_ref", 200)
        query = _text(query, "query")
        packet = brain_decision(self.bank, domain=domain, task_ref=task_ref)
        arm = packet["selected_strategy"]
        chosen = [] if arm == "cold" else self.recall(
            domain=domain, query=query, strategy=arm, limit=3)
        packet["lessons"] = [
            {"lesson_id": x["lesson_id"], "strategy": x["strategy"],
             "text": x["text"], "evidence_refs": x["evidence_refs"]}
            for x in chosen
        ]
        packet["native_skills"] = {
            "schema": SCHEMA, "query_sha256": sha256(query.encode()).hexdigest(),
            "selected_lessons": len(chosen),
            "retrieval": "same_domain_lexical",
            "independently_verified": False, "holdout_learning_proven": False}
        return packet

    def present(self, *, domain, task_ref, query):
        """Connector may explain but not change BEAN's journaled decision."""
        return connector_presentation_packet(
            self.decide(domain=domain, task_ref=task_ref, query=query))
