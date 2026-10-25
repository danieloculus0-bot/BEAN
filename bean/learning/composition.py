"""Bounded BEAN skill composition over its *already learned* symbolic rules.

BEAN enumerates parent-rule pairings and typed output joins, then tests all
candidate programs against separately supplied development examples. A unique
survivor is retained in BEAN's existing SHA-chained journal, linked to both
previously learned source rule IDs. Unknown and conflicting plans abstain.

This is a small program-induction grammar, not an open-domain planner, model
weight update, independent truth oracle, or permission to execute actions.
"""
from __future__ import annotations

from hashlib import sha256
import json

from bean.optimization.autodev import canonical
from .experimental import question_fingerprint
from .local_reasoner import _parse, _solve

SCHEMA = "bean.native.composition.v1"
JOINS = (
    "rank_second_in_first",
    "first_then_second",
    "second_then_first",
    "prefix_before_second",
    "suffix_after_second",
    "second_is_first",
)


def _text(value, name, max_len=1200):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= max_len:
        raise ValueError(name + " must be bounded nonempty text")
    return value.strip()


def _parts(question):
    """Typed structured mini-task. No free-text semantic parsing is claimed."""
    try:
        payload = json.loads(_text(question, "composite question"))
    except (ValueError, TypeError) as exc:
        raise ValueError("Composition needs JSON with exactly two parts") from exc
    if (not isinstance(payload, dict) or set(payload) != {"parts"}
            or not isinstance(payload["parts"], list)
            or len(payload["parts"]) != 2):
        raise ValueError("Composition needs exactly two structured parts")
    parts = [_text(v, "composition part", 400) for v in payload["parts"]]
    parsed = [_parse(part) for part in parts]
    if any(kind is None for kind, _ in parsed):
        raise ValueError("Composition part does not match an existing native rule grammar")
    return parsed


def _join(left, right, operator):
    if not isinstance(left, str) or not isinstance(right, str):
        return None
    if operator == "first_then_second":
        return left + "|" + right
    if operator == "second_then_first":
        return right + "|" + left
    if operator == "rank_second_in_first":
        return str(left.index(right) + 1) if right in left else None
    if operator == "prefix_before_second":
        return left.split(right, 1)[0] if right in left else None
    if operator == "suffix_after_second":
        return left.split(right, 1)[1] if right in left else None
    if operator == "second_is_first":
        return "YES" if left.startswith(right) else "NO"
    raise ValueError("Unknown composition operator")


def _predict(parsed, first, second, operator):
    if parsed[0][0] != first["grammar"] or parsed[1][0] != second["grammar"]:
        return None
    try:
        left = _solve(parsed[0][0], parsed[0][1], first["operation"])
        right = _solve(parsed[1][0], parsed[1][1], second["operation"])
    except (ValueError, TypeError, IndexError):
        return None
    return _join(left, right, operator)


class CompositionLearner:
    def __init__(self, bank):
        self.bank = bank

    def _parents(self):
        """Use only retained, typed, source-linked rules; no new hand-coded skill."""
        events = self.bank.journal.events()
        rules = [e["data"] for e in events if e["kind"] == "local_rule"]
        if len(rules) > 12:
            # Preserve bounded search instead of silently selecting a convenient
            # subset of memories, which would bias a claimed discovery.
            raise ValueError("Composition search needs a scoped inventory (max 12 rules)")
        return rules

    @staticmethod
    def _refuted_program_signatures(events):
        """Persist the lesson from bad feedback across renamed/retrained plans.

        Compare the actual composed procedure, not its training receipt:
        a fresh task ID or new examples cannot launder a refuted combination.
        """
        plans = {e["data"]["rule_id"]: e["data"] for e in events
                 if e["kind"] == "composed_rule"}
        inferences = {e["data"]["receipt_id"]: e["data"] for e in events
                      if e["kind"] == "inference"
                      and e["data"].get("purpose") == "local_composition_applied"
                      and isinstance(e["data"].get("receipt_id"), str)}
        signatures = set()
        for e in events:
            if e["kind"] != "feedback" or e["data"].get("matched") is not False:
                continue
            inference = inferences.get(e["data"].get("receipt_id"))
            if inference is None:
                continue
            for rule_id in inference.get("composed_rule_ids", []):
                plan = plans.get(rule_id)
                if plan is not None:
                    signatures.add((
                        plan["domain"], tuple(plan["parent_rule_ids"]),
                        plan["join"],
                    ))
        return signatures

    def propose(self, *, domain, task_ref, query):
        """Search plausible programs BEFORE teaching; do not treat a guess as truth."""
        domain = _text(domain, "domain", 100).casefold()
        task_ref = _text(task_ref, "task_ref", 200)
        try:
            parsed = _parts(query)
        except ValueError:
            return {"schema": SCHEMA, "status": "unsupported_question",
                    "hypotheses": [], "model_invoked": False,
                    "verified_outcome": False}
        programs = []
        refuted = self._refuted_program_signatures(self.bank.journal.events())
        parents = self._parents()
        for a in parents:
            for b in parents:
                if a["rule_id"] == b["rule_id"] or a["domain"] == b["domain"]:
                    continue
                for join in JOINS:
                    if (domain, (a["rule_id"], b["rule_id"]), join) in refuted:
                        continue
                    prediction = _predict(parsed, a, b, join)
                    if prediction is None or not prediction:
                        continue
                    proposal = {
                        "parent_rule_ids": [a["rule_id"], b["rule_id"]],
                        "parent_domains": [a["domain"], b["domain"]],
                        "join": join, "hypothetical_output": prediction,
                    }
                    proposal["proposal_id"] = sha256(canonical(proposal)).hexdigest()
                    programs.append(proposal)
        programs.sort(key=lambda item: (item["parent_rule_ids"], item["join"]))
        return {
            "schema": SCHEMA, "status": ("hypotheses_only" if programs else "abstain"),
            "domain": domain, "task_ref": task_ref,
            "question_sha256": question_fingerprint(query),
            "candidate_count": len(programs),
            "hypotheses": programs[:48],
            "truncated": len(programs) > 48,
            "proposal_only": True, "rule_retained": False,
            "independent_validation": False, "verified_outcome": False,
            "model_invoked": False, "actions_authorized": False,
        }

    def learn(self, *, domain, task_ref, examples, evidence_refs):
        domain = _text(domain, "domain", 100).casefold()
        task_ref = _text(task_ref, "task_ref", 200)
        if not isinstance(examples, list) or not 4 <= len(examples) <= 12:
            raise ValueError("Need 4..12 distinct development examples")
        if not isinstance(evidence_refs, (list, tuple)) or not 1 <= len(evidence_refs) <= 12:
            raise ValueError("Need 1..12 development evidence references")
        refs = [_text(ref, "source", 500) for ref in evidence_refs]
        cases = []
        for row in examples:
            if not isinstance(row, dict) or set(row) != {"question", "answer"}:
                raise ValueError("Development example needs exactly question and answer")
            question = _text(row["question"], "question")
            answer = _text(row["answer"], "answer", 100)
            cases.append((question_fingerprint(question), _parts(question), answer))
        hashes = [h for h, _, _ in cases]
        if len(set(hashes)) != len(hashes):
            raise ValueError("Development examples must have different question fingerprints")

        parents = self._parents()
        refuted = self._refuted_program_signatures(self.bank.journal.events())
        survivors = []
        considered = 0
        for first in parents:
            for second in parents:
                if (first["rule_id"] == second["rule_id"]
                        or first["domain"] == second["domain"]):
                    continue  # Independently learned domains are required.
                for operator in JOINS:
                    considered += 1
                    if (domain, (first["rule_id"], second["rule_id"]), operator) in refuted:
                        continue
                    if all(_predict(parsed, first, second, operator) == answer
                           for _, parsed, answer in cases):
                        survivors.append((first, second, operator))
        if len(survivors) != 1:
            return {
                "schema": SCHEMA, "status": "abstain",
                "reason": "ambiguous_composition" if survivors else "no_supported_composition",
                "surviving_programs": len(survivors),
                "programs_examined": considered,
                "rule_retained": False, "model_invoked": False,
            }
        first, second, operator = survivors[0]
        record = {
            "schema": SCHEMA, "domain": domain, "task_ref": task_ref,
            "parent_rule_ids": [first["rule_id"], second["rule_id"]],
            "parent_domains": [first["domain"], second["domain"]],
            "parent_grammars": [first["grammar"], second["grammar"]],
            "join": operator,
            "development_question_sha256": hashes,
            "development_examples": len(cases),
            "programs_examined": considered,
            "uniquely_supported_by_development": True,
            "evidence_refs": refs,
            "independent_validation": False,
            "model_invoked": False,
            "actions_authorized": False,
        }
        record["rule_id"] = sha256(canonical(record)).hexdigest()
        if any(e["kind"] == "composed_rule"
               and e["data"].get("rule_id") == record["rule_id"]
               for e in self.bank.journal.events()):
            return {"schema": SCHEMA, "status": "already_retained",
                    "rule_id": record["rule_id"], "rule_retained": True,
                    "model_invoked": False}
        tip = self.bank.record_composed_rule(record)
        return {
            "schema": SCHEMA, "status": "learned_composition",
            "rule_id": record["rule_id"], "parent_rule_ids": record["parent_rule_ids"],
            "join": operator, "programs_examined": considered,
            "journal_tip": tip, "rule_retained": True,
            "independent_validation": False, "model_invoked": False,
        }

    def reason(self, *, domain, task_ref, query):
        domain = _text(domain, "domain", 100).casefold()
        task_ref = _text(task_ref, "task_ref", 200)
        try:
            parsed = _parts(query)
        except ValueError:
            return self._abstain("unsupported_composite_question")
        events = self.bank.journal.events()
        parents = {e["data"]["rule_id"]: e["data"] for e in events
                   if e["kind"] == "local_rule"}
        plans = [e["data"] for e in events if e["kind"] == "composed_rule"
                 and e["data"]["domain"] == domain]
        if not plans:
            return self._abstain("no_retained_composition_in_domain")
        refuted = self._refuted_program_signatures(events)
        active = [plan for plan in plans if
                  (domain, tuple(plan["parent_rule_ids"]), plan["join"])
                  not in refuted]
        if not active:
            return self._abstain("composition_has_refuted_host_feedback")
        predictions = []
        for plan in active:
            a, b = plan["parent_rule_ids"]
            if a not in parents or b not in parents:
                raise ValueError("Composed rule missing immutable parent")
            prediction = _predict(parsed, parents[a], parents[b], plan["join"])
            if prediction is not None:
                predictions.append((prediction, plan))
        if not predictions or len(set(x for x, _ in predictions)) != 1:
            return self._abstain("conflicting_or_inapplicable_compositions")
        answer = predictions[0][0]
        if not answer:
            return self._abstain("empty_composition_result")
        records = [p for _, p in predictions]
        source_ids = list(dict.fromkeys(
            r for plan in records for r in plan["parent_rule_ids"]))
        overlap = question_fingerprint(query) in {
            h for plan in records for h in plan["development_question_sha256"]}
        record = {
            "schema": "bean.native.reasoning.inference.v1",
            "purpose": "local_composition_applied",
            "domain": domain, "task_ref": task_ref,
            "query": query, "answer": answer,
            "model_id": SCHEMA, "provider_kind": "native_local",
            "provider_response_id": None,
            "source_refs": list(dict.fromkeys(
                r for plan in records for r in plan["evidence_refs"])),
            "parent_rule_ids": source_ids,
            "composed_rule_ids": [p["rule_id"] for p in records],
            "selected_strategy": "native_composition",
            "verified_outcome": False,
            "development_overlap": overlap,
            "event_sequence": len(events) + 1,
        }
        record["receipt_id"] = sha256(canonical(record)).hexdigest()
        tip = self.bank.record_inference(record)
        return {
            "schema": SCHEMA, "status": "locally_solved", "answer": answer,
            "receipt_id": record["receipt_id"], "journal_tip": tip,
            "model_invoked": False, "external_cost_usd": 0,
            "rules_used": source_ids,
            "composed_rule_ids": record["composed_rule_ids"],
            "trace": ["parse:two_known_rule_inputs",
                      "enumerated learned parents",
                      "apply:" + predictions[0][1]["join"]],
            "development_overlap": overlap,
            "independent_validation": False,
            "verified_outcome": False,
        }

    @staticmethod
    def _abstain(reason):
        return {"schema": SCHEMA, "status": "abstain", "reason": reason,
                "answer": None, "model_invoked": False,
                "external_cost_usd": 0, "verified_outcome": False}
