"""BEAN's own CPU-only hypothesis induction and reasoning over small rule families.

Not an LLM or a claim of open-domain intelligence. BEAN proposes candidate
procedures, falsifies them against observed examples, retains a unique surviving
rule in its existing SHA ledger, and applies it to unseen cases after restart.
Unsupported/ambiguous questions cause abstention, NOT guessed answers or a
silent external API call. No nonstandard packages, network or GPU required.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from bean.optimization.autodev import canonical

VERSION = "bean.native.symbolic.v1"
TAG = re.compile(r"(?<![a-zA-Z0-9])([A-Z])([0-9])(?![a-zA-Z0-9])")
GAUGE = re.compile(r"(?<![a-zA-Z0-9])([A-Z])=(-?[0-9]+)(?![a-zA-Z0-9])")
OPS = {
    "tags": ("digit_desc", "digit_asc", "letter_asc", "letter_desc"),
    "gauge": ("median", "minimum", "maximum"),
}


def _text(value, name, limit=1000):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(name + " must be bounded nonempty text")
    return value.strip()


def _parse(question):
    q = _text(question, "question")
    # Three distinct labels and numbers, not an arbitrary comma sequence.
    gauges = [(m.group(1), int(m.group(2))) for m in GAUGE.finditer(q)]
    tags = [(m.group(1), int(m.group(2))) for m in TAG.finditer(q)]
    def valid(items):
        return (len(items) >= 3 and len(items) <= 8
                and len({x[0] for x in items}) == len(items)
                and len({x[1] for x in items}) == len(items))
    if valid(gauges) and not valid(tags):
        return "gauge", gauges
    if valid(tags) and not valid(gauges):
        return "tags", tags
    return None, []


def _solve(grammar, values, operation):
    if grammar == "tags":
        if operation == "digit_desc":
            ordered = sorted(values, key=lambda x: -x[1])
        elif operation == "digit_asc":
            ordered = sorted(values, key=lambda x: x[1])
        elif operation == "letter_asc":
            ordered = sorted(values, key=lambda x: x[0])
        elif operation == "letter_desc":
            ordered = sorted(values, key=lambda x: x[0], reverse=True)
        else:
            raise ValueError("Unknown numeric-tag rule")
        return "".join(x[0] for x in ordered)
    if grammar == "gauge":
        ordered = sorted(values, key=lambda x: x[1])
        if operation == "minimum":
            return ordered[0][0]
        if operation == "median":
            return ordered[len(ordered)//2][0] if len(ordered) % 2 else None
        if operation == "maximum":
            return ordered[-1][0]
    raise ValueError("Unknown rule or unsupported even-sized median")


class LocalReasoner:
    """A deterministic local experimental reasoner sharing Core ExperienceBank."""

    def __init__(self, bank):
        self.bank = bank

    def learn(self, *, domain, task_ref, examples, evidence_refs):
        domain = _text(domain, "domain", 100).casefold()
        task_ref = _text(task_ref, "task_ref", 200)
        if (not isinstance(examples, list) or not 3 <= len(examples) <= 20
                or not isinstance(evidence_refs, (tuple, list))
                or not 1 <= len(evidence_refs) <= 15):
            raise ValueError("Three or more examples and source references required")
        refs = [_text(r, "evidence reference", 500) for r in evidence_refs]
        parsed = []
        for row in examples:
            if not isinstance(row, dict) or set(row) != {"question", "answer"}:
                raise ValueError("Each example requires question and answer")
            q = _text(row["question"], "development question")
            a = _text(row["answer"], "development answer", 30)
            grammar, values = _parse(q)
            if not grammar:
                raise ValueError("No supported symbolic grammar")
            parsed.append((q, a, grammar, values))
        if (len({x[0].casefold() for x in parsed}) != len(parsed)
                or len({x[2] for x in parsed}) != 1):
            raise ValueError("Development questions must be distinct and share grammar")
        grammar = parsed[0][2]
        viable = [op for op in OPS[grammar]
                  if all(_solve(grammar, values, op) == expected
                         for _, expected, _, values in parsed)]
        # *Ambiguous* or internally contradictory teaching is not evidence
        # of a unique general rule. Never pick an arbitrary winner.
        if len(viable) != 1:
            return {"schema": VERSION, "status": "abstain",
                    "reason": ("ambiguous_hypothesis" if viable
                               else "observations_contradict_all_candidates"),
                    "surviving_hypotheses": viable,
                    "candidate_count": len(OPS[grammar]),
                    "model_invoked": False, "lesson_retained": False}
        rule = {
            "schema": VERSION, "domain": domain,
            "task_ref": task_ref, "grammar": grammar,
            "operation": viable[0], "evidence_refs": refs,
            "examples": [{
                "question_sha256": sha256(q.encode()).hexdigest(),
                "answer_sha256": sha256(a.encode()).hexdigest()
            } for q, a, _, _ in parsed],
            "development_examples": len(parsed),
            "independent_validation": False,
            "external_model_used": False,
        }
        rule["rule_id"] = sha256(canonical(rule)).hexdigest()
        existing = [r["data"] for r in self.bank.journal.events()
                    if r["kind"] == "local_rule"
                    and r["data"].get("rule_id") == rule["rule_id"]]
        if existing:
            return {"schema": VERSION, "status": "already_retained",
                    "rule_id": rule["rule_id"], "grammar": grammar,
                    "operation": viable[0], "lesson_retained": True,
                    "model_invoked": False}
        tip = self.bank.record_local_rule(rule)
        return {"schema": VERSION, "status": "learned_local_rule",
                "rule_id": rule["rule_id"], "grammar": grammar,
                "operation": viable[0], "development_examples": len(parsed),
                "journal_tip": tip, "lesson_retained": True,
                "independent_validation": False, "model_invoked": False}

    def reason(self, *, domain, task_ref, question):
        domain = _text(domain, "domain", 100).casefold()
        task_ref = _text(task_ref, "task_ref", 200)
        question = _text(question, "question")
        grammar, values = _parse(question)
        if not grammar:
            return self._abstain("unsupported_question_structure")
        rules = [e["data"] for e in self.bank.journal.events()
                 if e["kind"] == "local_rule" and e["data"]["domain"] == domain
                 and e["data"]["grammar"] == grammar]
        if not rules:
            return self._abstain("no_learned_rule_in_domain")
        solutions = []
        for r in rules:
            predicted = _solve(grammar, values, r["operation"])
            if predicted is not None:
                solutions.append((predicted, r))
        if not solutions or len({a for a, _ in solutions}) != 1:
            return self._abstain("conflicting_or_inapplicable_rules")
        answer = solutions[0][0]
        record = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": "local_rule_applied",
            "domain": domain, "task_ref": task_ref, "query": question,
            "answer": answer, "model_id": VERSION,
            "provider_kind": "native_local", "provider_response_id": None,
            "source_refs": list(dict.fromkeys(
                ref for _, rule in solutions for ref in rule["evidence_refs"])),
            "local_rule_ids": [rule["rule_id"] for _, rule in solutions],
            "selected_strategy": "native_symbolic",
            "verified_outcome": False,
            "event_sequence": len(self.bank.journal.events()) + 1,
        }
        record["receipt_id"] = sha256(canonical(record)).hexdigest()
        tip = self.bank.record_inference(record)
        return {"schema": VERSION, "status": "locally_solved",
                "answer": answer, "receipt_id": record["receipt_id"],
                "journal_tip": tip, "model_invoked": False,
                "external_cost_usd": 0, "rules_used": record["local_rule_ids"],
                "trace": ["parse:" + grammar,
                          "test retained rule family",
                          "apply:" + solutions[0][1]["operation"]],
                "independent_validation": False,
                "verified_outcome": False}

    @staticmethod
    def _abstain(reason):
        return {"schema": VERSION, "status": "abstain", "reason": reason,
                "answer": None, "model_invoked": False,
                "external_cost_usd": 0, "verified_outcome": False}
