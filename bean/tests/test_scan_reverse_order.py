"""Order-sensitive held-out SCAN evaluation of BEAN's existing source-induced composer.

Use the externally authored, pinned add-primitive-jump split. The diagnostic
cohort is selected by a frozen hash from test commands with exactly one
observable reverse-order 'after' split. Gold labels select the diagnostic
cohort, but never enter candidate training or prediction. All policies share
the same 1,024 source labels and prediction budget.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_scan_reverse_order
python -m bean.tests.test_scan_reverse_order --report
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
from bean.tests.test_external_scan_composition import FILES, _digest, _fetch
from bean.tests.test_scan_operator_composition import OperatorComposer, _ref, _restore
from bean.tests.test_scan_phrase_roles import (
    PhraseRoleSlots, _restore_phrase, _source_training,
)

SCHEMA = "bean.scan_reverse_order.v1"
SELECTION_SEED = "bean-scan-reverse-order-independent-20261102"
TEST_BUDGET = 96
TRAIN_BUDGET = 1024
POLICIES = ("learned", "phrase", "blind")


def _eligible(train, test):
    """Scorer-only selection, independent of model outputs or training subset."""
    all_gold = dict(train)
    all_gold.update(test)
    choices = []
    for command, truth in test.items():
        if command.count(" after ") != 1:
            continue
        left, right = command.split(" after ")
        if left not in all_gold or right not in all_gold:
            continue
        a, b = all_gold[left], all_gold[right]
        if a == b or truth != b + " " + a or truth == a + " " + b:
            continue
        choices.append(command)
    return sorted(choices, key=lambda c: (
        sha256((SELECTION_SEED + ":" + c).encode()).hexdigest(), c))


def _native_restart(selected, command):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "scan-reverse.sqlite"
        core = NativeReasoningService(path, model=None)
        try:
            for source, output in list(selected.items())[:24]:
                core.propose_instruction(
                    domain="public-scan-source",
                    instruction="Source command " + source + " => " + output,
                    evidence_refs=[_ref(source), "scan:gitblob:" + FILES["train"][1]],
                )
            before = [h["lesson_id"] for h in core.recall_analogies(
                domain="public-scan-holdout", query=command, limit=8)]
            count = len(core.bank.journal.events())
        finally:
            core.close()
        reopened = NativeReasoningService(path, model=None)
        try:
            after = [h["lesson_id"] for h in reopened.recall_analogies(
                domain="public-scan-holdout", query=command, limit=8)]
            if before != after or len(reopened.bank.journal.events()) != count:
                raise AssertionError("Native SQLite replay drift")
        finally:
            reopened.close()
    return True


def run_report(train, test, source_hashes):
    selected = _source_training(train)
    if len(selected) != TRAIN_BUDGET:
        raise AssertionError("Changed fixed training budget")
    eligible = _eligible(train, test)
    if len(eligible) < TEST_BUDGET:
        raise ValueError("Insufficient independently sourced reverse-order cases: "
                         + str(len(eligible)))
    commands = eligible[:TEST_BUDGET]
    source_blob = "scan:gitblob:" + FILES["train"][1]
    learned, ls = _restore(OperatorComposer(selected, source_blob))
    blind, bs = _restore(OperatorComposer(
        selected, source_blob, blind_left_first=True))
    phrase, ps = _restore_phrase(PhraseRoleSlots(selected, source_blob))
    models = {"learned": learned, "phrase": phrase, "blind": blind}
    states = {"learned": ls["state_sha256"], "phrase": ps["state_sha256"],
              "blind": bs["state_sha256"]}
    # Freeze every model output before looking up the held-out labels.
    frozen = {name: [model.predict(command) for command in commands]
              for name, model in models.items()}
    valid_refs = {_ref(command) for command in selected}
    rows = []
    for index, command in enumerate(commands):
        results = {name: frozen[name][index] for name in POLICIES}
        if any(not set(item["evidence_refs"]).issubset(valid_refs)
               for item in results.values()):
            raise AssertionError("Unselected evidence reference")
        truth = test[command]
        left, right = command.split(" after ")
        row = {
            "command": command, "left": left, "right": right,
            "scorer_only_output": truth,
            "predictions": {name: results[name]["prediction"] for name in POLICIES},
            "correct": {name: results[name]["prediction"] == truth
                        for name in POLICIES},
            "reasons": {name: results[name]["reason"] for name in POLICIES},
            "composed": {name: results[name].get("composed", False)
                         for name in POLICIES},
            "evidence_refs": {name: results[name]["evidence_refs"]
                              for name in POLICIES},
            "state_sha256": states,
        }
        row["case_sha256"] = _digest(row)
        rows.append(row)
    scores = {name: sum(row["correct"][name] for row in rows)
              for name in POLICIES}
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "benchmark": "https://github.com/brendenlake/SCAN",
        "split": "add_prim_jump",
        "source_hashes": source_hashes,
        "selection_seed": SELECTION_SEED,
        "eligible_pool": len(eligible),
        "training_budget": len(selected),
        "training_rows": [[command, output] for command, output in selected.items()],
        "training_rows_sha256": _digest(list(selected.items())),
        "holdout_budget": len(rows),
        "state_sha256": states,
        "snapshot_restart_verified": True,
        "native_sqlite_restart_verified": _native_restart(selected, commands[0]),
        "scores_exact_match": scores,
        "coverage": {name: sum(row["predictions"][name] is not None
                               for row in rows) for name in POLICIES},
        "paired_learned_minus_blind": [
            int(row["correct"]["learned"]) - int(row["correct"]["blind"])
            for row in rows],
        "paired_learned_minus_phrase": [
            int(row["correct"]["learned"]) - int(row["correct"]["phrase"])
            for row in rows],
        "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "candidate_failures": [
            {"command": row["command"], "reason": row["reasons"]["learned"]}
            for row in rows if not row["correct"]["learned"]],
        "limitations": [
            "Scorer-only gold labels select reverse-order diagnostic cases",
            "Single externally authored synthetic SCAN task family",
            "Same 1,024 source labels and fixed inference budget for all controls",
            "Source-trained operator evidence may not cover all held-out subcommands",
            "All errors and abstentions retained as case-level negative evidence",
        ],
    }


class ReverseOrderControls(unittest.TestCase):
    def test_reverse_order_filter_is_oracle_only(self):
        train = {"walk": "I_WALK", "run": "I_RUN"}
        test = {"walk after run": "I_RUN I_WALK",
                "run after walk": "I_WALK I_RUN",
                "walk and run": "I_WALK I_RUN",
                "walk after walk": "I_WALK I_WALK"}
        result = _eligible(train, test)
        self.assertEqual(set(result), {"walk after run", "run after walk"})
        self.assertEqual(result, _eligible(train, dict(reversed(list(test.items())))))

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_external_reverse_order_holdout(self):
        data, hashes = _fetch()
        report = run_report(data["train"], data["test"], hashes)
        self.assertEqual(report["holdout_budget"], TEST_BUDGET)
        self.assertTrue(report["snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_report(data["train"], data["test"], hashes),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
