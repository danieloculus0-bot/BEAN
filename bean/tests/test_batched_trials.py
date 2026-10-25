"""BEAN uses one inference per control arm without leaking outcome labels."""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from bean.learning import BEANReasoningSkills, ExperienceBank, TrialCase
from bean.learning.batched_trials import run_batched_paired_trial
from bean.learning.experimental import material_for


class BatchingMock:
    model_id = "fixture-batched-model"
    provider_kind = "synthetic_fixture"

    def __init__(self):
        self.calls = []

    def complete_batch(self, items):
        self.calls.append(items)
        assert all(set(item) == {"task_id", "question", "context"}
                   for item in items)
        assert len(items) in (2, 4)
        answer = {}
        for x in items:
            # Only a relevant memory can provide the fictional sorting rule.
            answer[x["task_id"]] = (
                ",".join(sorted(x["question"].split(":")[-1].strip().split(",")))
                if "SORT_COMMAS" in x["context"] else "UNKNOWN"
            )
        return answer


class BatchingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "bean.sqlite3"
        self.bank = ExperienceBank(self.path)
        self.addCleanup(self.bank.close)
        self.bean = BEANReasoningSkills(self.bank)
        self.bean.reflect(
            domain="sort", task_id="dev", observed="unsorted tags",
            expected="sorted tags", adjustment_hypothesis="SORT_COMMAS sort a,b,c",
            evidence_refs=["fixture:dev"])
        self.bean.retain_skill(
            domain="sort", name="SORT_COMMAS", steps=["SORT_COMMAS sort a,b,c"],
            passed=True, evidence_refs=["fixture:skill"])
        self.bean.propose_instruction(
            domain="sort", instruction="SORT_COMMAS sort a,b,c",
            evidence_refs=["fixture:instruction"])
        self.bean.reflect(
            domain="unrelated", task_id="irrelevant", observed="orange",
            expected="green", adjustment_hypothesis="UNRELATED_COLOR_ONLY",
            evidence_refs=["fixture:placebo"])
        self.selection = [
            TrialCase("s1", "sort", "sort comma tags: z,b", "b,z"),
            TrialCase("s2", "sort", "sort comma tags: q,a", "a,q"),
        ]
        self.holdout = [
            TrialCase("h1", "sort", "sort comma tags: t,d", "d,t"),
            TrialCase("h2", "sort", "sort comma tags: w,c", "c,w"),
            TrialCase("h3", "sort", "sort comma tags: g,f", "f,g"),
            TrialCase("h4", "sort", "sort comma tags: p,b", "b,p"),
        ]

    def test_selected_strategy_and_restarted_holdout_use_only_eight_calls(self):
        model = BatchingMock()
        winner = self.bean.evaluate_and_select(
            domain="sort", cases=self.selection, model=model,
            judge=lambda expected, answer: expected == answer, batched=True)
        self.assertEqual(winner["selection"]["arm"], "reflection")
        self.assertEqual(winner["trial"]["scores"], {
            "cold": 0, "reflection": 2, "skill": 2,
            "prompt": 2, "placebo": 0})
        self.assertEqual(len(model.calls), 5)
        self.assertEqual(winner["trial"]["provider_requests"], 5)
        # Controls isolated: each call sees only its own arm.
        for arm, items in zip(winner["trial"]["arms"], model.calls):
            all_contexts = [item["context"] for item in items]
            if arm in ("cold", "placebo"):
                self.assertTrue(all("SORT_COMMAS" not in x for x in all_contexts))
            else:
                self.assertTrue(all("SORT_COMMAS" in x for x in all_contexts))
        self.bank.close()
        new_bank = ExperienceBank(self.path)
        try:
            new_bean = BEANReasoningSkills(new_bank)
            after = new_bean.evaluate_holdout(
                domain="sort", cases=self.holdout, model=model,
                judge=lambda expected, answer: expected == answer, batched=True)
            self.assertEqual(after["trial"]["scores"], {
                "cold": 0, "placebo": 0, "adaptive": 4})
            self.assertEqual(after["trial"]["provider_requests"], 3)
            self.assertEqual(len(model.calls), 8)
            self.assertEqual(len(after["trial"]["records"]), 12)
            self.assertEqual(after["trial"]["batching_policy"],
                             "one_isolated_request_per_arm_v1")
            for row in after["trial"]["records"]:
                task = next(x for x in self.holdout if x.task_id == row["task_id"])
                ctx = material_for(new_bank, row["arm"], "sort",
                                   query=task.public_question)
                self.assertEqual(row["context_sha256"],
                                 sha256(ctx.encode()).hexdigest())
        finally:
            new_bank.close()

    def test_malformed_batch_is_rejected_without_journal_credit(self):
        class MissingAnswer(BatchingMock):
            def complete_batch(self, items):
                return {items[0]["task_id"]: "UNKNOWN"}

        n = len(self.bank.journal.events())
        with self.assertRaisesRegex(ValueError, "omitted"):
            run_batched_paired_trial(
                bank=self.bank, cases=self.selection, model=MissingAnswer(),
                judge=lambda a, b: a == b)
        self.assertEqual(len(self.bank.journal.events()), n)

    def test_recovery_source_hashes_are_full_sha256_digests(self):
        from bean.evaluation.nemotron_batched_recovery import ORIGINAL_SHA256
        self.assertEqual(set(ORIGINAL_SHA256), {
            "report.json", "experience.sqlite3", "provider_calls.jsonl"})
        self.assertTrue(all(
            len(value) == 64 and all(char in "0123456789abcdef" for char in value)
            for value in ORIGINAL_SHA256.values()))

    def test_incompatible_batch_repeat_budget_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "one replicate"):
            self.bean.evaluate_and_select(
                domain="sort", cases=self.selection, model=BatchingMock(),
                judge=lambda a,b: a == b, batched=True, replicates=2)


if __name__ == "__main__":
    unittest.main()
