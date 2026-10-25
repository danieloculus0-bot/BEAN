"""Live-model experiment orchestration tested with explicit MOCK provider."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bean.learning.experimental import ExperienceBank
from bean.learning.live_lab026 import create_strategy_lessons,run_local_trial


class FakeModel:
    provider_kind="synthetic_fixture"
    model_id="fake-generation-model"
    def __init__(self, *args,**kwargs):
        self.questions=[]
    def complete(self,question,context):
        self.questions.append(question)
        return "rule hypothesized from feedback"


class LocalFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.development={"schema":"bean.lab026.development.v1","cases":[
            {"id":"train1","domain":"sorting","question":"sort c,b,a",
             "observed":"unknown","expected":"a,b,c","evidence_ref":"lab:train1"},
            {"id":"train2","domain":"sorting","question":"sort e,d",
             "observed":"unknown","expected":"d,e","evidence_ref":"lab:train2"}]}
        self.holdout={"schema":"bean.lab026.holdout.v1","cases":[
            {"id":"test1","domain":"sorting","question":"sort m,a","expected":"a,m"},
            {"id":"test2","domain":"sorting","question":"sort z,x","expected":"x,z"}]}

    def test_feedback_authors_three_distinct_persistent_hypotheses(self):
        bank=ExperienceBank(self.root/"bank.sqlite")
        fake=FakeModel()
        ids=create_strategy_lessons(bank,fake,self.development,"sorting")
        self.assertEqual(len(ids),3)
        self.assertEqual(len(bank.lessons()),3)
        self.assertTrue(all("train1" in prompt for prompt in fake.questions))
        self.assertEqual(len(create_strategy_lessons(bank,fake,self.development,"sorting")),3)
        self.assertEqual(len(fake.questions),3)
        bank.close()
        restored=ExperienceBank(self.root/"bank.sqlite")
        self.assertEqual(len(restored.lessons()),3)
        restored.close()

    def test_live_trial_report_does_not_mutate_journal_receipt(self):
        development=self.root/"development.json"
        held=self.root/"holdout.json"
        development.write_text(json.dumps(self.development))
        held.write_text(json.dumps(self.holdout))
        with patch("bean.learning.live_lab026.LocalOllamaTrialModel",FakeModel):
            report=run_local_trial(development_path=development,
                holdout_path=held,output=self.root/"output",
                domain="sorting",replicates=1)
        self.assertFalse(report["learning_proven"])
        self.assertFalse(report["placebo_context_present"])
        self.assertEqual(report["trial_receipt"]["provider_kind"],"synthetic_fixture")
        bank=ExperienceBank(self.root/"output"/"persistent_adaptive_ledger.sqlite")
        self.assertEqual(bank.journal.events()[-1]["data"],
                         {k:v for k,v in report["trial_receipt"].items()
                          if k!="journal_tip"})
        bank.close()

    def test_holdout_identity_overlap_rejected(self):
        development=self.root/"development.json"
        held=self.root/"holdout.json"
        development.write_text(json.dumps(self.development))
        broken=dict(self.holdout)
        broken["cases"]=[dict(x) for x in self.holdout["cases"]]
        broken["cases"][0]["id"]="train1"
        held.write_text(json.dumps(broken))
        with self.assertRaisesRegex(ValueError,"not overlap"):
            run_local_trial(development_path=development,holdout_path=held,
                            output=self.root/"reject",domain="sorting")


if __name__=="__main__":
    unittest.main()
