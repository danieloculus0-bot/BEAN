"""Counterfactual nonce-language order probe for BEAN's existing OperatorComposer.

Twelve independently seeded, fully synthetic vocabularies. Each has 22 labeled
source commands and 16 unseen two-clause queries. The oracle is evaluated only
after candidate and matched controls freeze predictions. No source vocabulary,
operator names or answer labels are taken from a private dataset.

python -m unittest -v bean.tests.test_nonce_operator_order
python -m bean.tests.test_nonce_operator_order --report
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService
from bean.tests.test_external_scan_composition import _digest
from bean.tests.test_scan_operator_composition import (
    OperatorComposer, _ref, _restore,
)
from bean.tests.test_scan_phrase_roles import PhraseRoleSlots, _restore_phrase

SCHEMA = "bean.nonce_operator_order.v1"
SEEDS = tuple(range(4100, 4112))
SOURCE_BUDGET = 22
QUERIES_PER_SEED = 16
POLICIES = ("learned", "phrase", "blind")
MODIFIERS = {"doubled": 2, "tripled": 3}


def _nonce(seed, role, index):
    digest = sha256(f"nonce-order-v1:{seed}:{role}:{index}".encode()).digest()
    return "n" + "".join(chr(97 + b % 26) for b in digest[:9])


def _actions(verb, count):
    return " ".join(["I_" + verb.upper()] * count)


def _oracle(command, verbs, operators):
    words = command.split()
    if len(words) == 1 and words[0] in verbs:
        return _actions(words[0], 1)
    if len(words) == 2 and words[0] in verbs and words[1] in MODIFIERS:
        return _actions(words[0], MODIFIERS[words[1]])
    if len(words) == 3 and words[0] in verbs and words[2] in verbs:
        order = operators.get(words[1])
        if order:
            parts = [_actions(words[0], 1), _actions(words[2], 1)]
            return " ".join(parts if order == "lr" else reversed(parts))
    if (len(words) == 5 and words[0] in verbs and words[1] in MODIFIERS
            and words[3] in verbs and words[4] in MODIFIERS):
        order = operators.get(words[2])
        if order:
            parts = [_actions(words[0], MODIFIERS[words[1]]),
                     _actions(words[3], MODIFIERS[words[4]])]
            return " ".join(parts if order == "lr" else reversed(parts))
    raise ValueError("Command outside predeclared independent grammar")


def _domain(seed):
    verbs = [_nonce(seed, "verb", i) for i in range(6)]
    ops = [_nonce(seed, "operator", i) for i in range(2)]
    if len(set(verbs + ops)) != 8:
        raise AssertionError("Nonce token collision")
    # Exactly one left-first and one right-first operator per world.
    orders = {ops[0]: "rl" if seed % 2 == 0 else "lr",
              ops[1]: "lr" if seed % 2 == 0 else "rl"}
    source = {}
    for verb in verbs:
        source[verb] = _oracle(verb, verbs, orders)
        for modifier in MODIFIERS:
            command = f"{verb} {modifier}"
            source[command] = _oracle(command, verbs, orders)
    for operator in ops:
        for a, b in ((0, 1), (2, 3)):
            command = f"{verbs[a]} {operator} {verbs[b]}"
            source[command] = _oracle(command, verbs, orders)
    if len(source) != SOURCE_BUDGET:
        raise AssertionError("Source label budget drift")
    queries = []
    for operator in ops:
        pairs = [(a, b) for a in verbs for b in verbs if a != b]
        pairs.sort(key=lambda pair: sha256(
            f"{seed}:{operator}:{pair[0]}:{pair[1]}".encode()).hexdigest())
        for index, (left, right) in enumerate(pairs[:8]):
            lm = "doubled" if index % 2 == 0 else "tripled"
            rm = "tripled" if index % 2 == 0 else "doubled"
            queries.append(f"{left} {lm} {operator} {right} {rm}")
    if len(queries) != QUERIES_PER_SEED or len(set(queries)) != len(queries):
        raise AssertionError("Invalid holdout selection")
    if set(source) & set(queries):
        raise AssertionError("Source/test leakage")
    return {
        "seed": seed, "verbs": verbs, "operators": orders,
        "source_rows": [[k, v] for k, v in sorted(source.items())],
        "holdout_queries": queries,
    }


def _native_restart(spec):
    """Reuse the canonical native SQLite reasoning service on a temporary DB."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "nonce-reasoning.sqlite"
        service = NativeReasoningService(db, model=None)
        try:
            for command, output in spec["source_rows"]:
                service.propose_instruction(
                    domain="synthetic-nonce-source",
                    instruction=f"Nonce training {command} => {output}",
                    evidence_refs=[_ref(command),
                                   "synthetic:nonce-order:" + str(spec["seed"])])
            query = spec["holdout_queries"][0]
            before = [h["lesson_id"] for h in service.recall_analogies(
                domain="synthetic-nonce-holdout", query=query, limit=8)]
            events = len(service.bank.journal.events())
        finally:
            service.close()
        reopened = NativeReasoningService(db, model=None)
        try:
            after = [h["lesson_id"] for h in reopened.recall_analogies(
                domain="synthetic-nonce-holdout", query=query, limit=8)]
            if before != after or len(reopened.bank.journal.events()) != events:
                raise AssertionError("Canonical native SQLite restart drift")
        finally:
            reopened.close()
    return True


def run_report():
    specs, rows = [], []
    for seed in SEEDS:
        spec = _domain(seed)
        source = dict(spec["source_rows"])
        source_blob = "synthetic:sha256:" + _digest(spec["source_rows"])
        learned, ls = _restore(OperatorComposer(source, source_blob))
        blind, bs = _restore(OperatorComposer(
            source, source_blob, blind_left_first=True))
        phrase, ps = _restore_phrase(PhraseRoleSlots(source, source_blob))
        models = {"learned": learned, "phrase": phrase, "blind": blind}
        states = {"learned": ls["state_sha256"],
                  "phrase": ps["state_sha256"],
                  "blind": bs["state_sha256"]}
        spec["source_sha256"] = _digest(spec["source_rows"])
        spec["state_sha256"] = states
        spec["snapshot_restart_verified"] = True
        valid_refs = {_ref(command) for command in source}
        # Freeze predictions without passing any heldout answer to a model.
        frozen = {
            name: [model.predict(query) for query in spec["holdout_queries"]]
            for name, model in models.items()
        }
        for index, command in enumerate(spec["holdout_queries"]):
            prediction = {name: frozen[name][index]["prediction"]
                          for name in POLICIES}
            refs = {name: frozen[name][index]["evidence_refs"]
                    for name in POLICIES}
            if any(not set(value).issubset(valid_refs) for value in refs.values()):
                raise AssertionError("Prediction cites unobserved source")
            operator = command.split()[2]
            truth = _oracle(command, spec["verbs"], spec["operators"])
            row = {
                "seed": seed, "command": command, "operator": operator,
                "expected_order": spec["operators"][operator],
                "scorer_only_output": truth,
                "predictions": prediction,
                "correct": {name: prediction[name] == truth for name in POLICIES},
                "evidence_refs": refs,
                "reasons": {name: frozen[name][index]["reason"]
                            for name in POLICIES},
                "composed": {name: frozen[name][index].get("composed", False)
                             for name in POLICIES},
                "state_sha256": states,
            }
            row["case_sha256"] = _digest(row)
            rows.append(row)
        specs.append(spec)
    native_restart = _native_restart(specs[0])
    by_order = {}
    for order in ("lr", "rl"):
        subset = [r for r in rows if r["expected_order"] == order]
        by_order[order] = {
            "cases": len(subset),
            "scores": {p: sum(r["correct"][p] for r in subset) for p in POLICIES},
            "paired_learned_minus_blind": [
                int(r["correct"]["learned"]) - int(r["correct"]["blind"])
                for r in subset],
            "paired_learned_minus_phrase": [
                int(r["correct"]["learned"]) - int(r["correct"]["phrase"])
                for r in subset],
        }
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "seed_range": list(SEEDS), "source_labels_per_seed": SOURCE_BUDGET,
        "queries_per_seed": QUERIES_PER_SEED,
        "domain_specs": specs, "domain_specs_sha256": _digest(specs),
        "snapshot_restart_verified": True,
        "native_sqlite_restart_verified": native_restart,
        "by_order": by_order,
        "case_receipts": rows, "case_receipts_sha256": _digest(rows),
        "candidate_failures": [
            {"seed": r["seed"], "command": r["command"],
             "reason": r["reasons"]["learned"]}
            for r in rows if not r["correct"]["learned"]],
        "limitations": [
            "Generated nonce worlds share a simple grammar and independent oracle",
            "No real-world semantic transfer or independent acquired task domain",
            "The same 22 source labels are provided to all three policies per seed",
            "Synthetic reverse-order contrasts test rule use, not language understanding",
            "Source and model JSON restarts plus temporary native SQLite replay only",
        ],
    }


class NonceOperatorControls(unittest.TestCase):
    def test_nonce_source_is_independent_and_balanced(self):
        for seed in SEEDS:
            spec = _domain(seed)
            self.assertEqual(len(spec["source_rows"]), SOURCE_BUDGET)
            self.assertEqual(len(spec["holdout_queries"]), QUERIES_PER_SEED)
            self.assertEqual(set(spec["operators"].values()), {"lr", "rl"})
            self.assertFalse(
                {row[0] for row in spec["source_rows"]} &
                set(spec["holdout_queries"]))
            self.assertEqual(spec, _domain(seed))

    def test_frozen_paired_order_probe_and_restart(self):
        report = run_report()
        self.assertEqual(len(report["case_receipts"]), 192)
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertEqual(report["by_order"]["lr"]["cases"], 96)
        self.assertEqual(report["by_order"]["rl"]["cases"], 96)
        self.assertTrue(report["native_sqlite_restart_verified"])
        self.assertTrue(report["snapshot_restart_verified"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
