"""Small isolated tests of BEAN CAD-choice and independent refusal gates.

No model credentials, inference, new CAD geometry, or robot hardware needed.
"""
from __future__ import annotations
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments.robot_cad_peer import bean_design_request as author
from experiments.robot_cad_peer import cad_qa_runner as judge


class CADChoiceTests(unittest.TestCase):
    def valid(self):
        return {
            "length_mm":35.0,"width_mm":32.0,"height_mm":22.0,
            "axle_bore_d_mm":6.70,"bolt_bore_d_mm":4.35,
            "rationale":"Reduce material while preserving axle and bolt clearances.",
        }

    def test_real_distinct_proposal_parsed(self):
        params,why=author.parse_model_json(json.dumps(self.valid()))
        self.assertEqual(params["length_mm"],35.0)
        self.assertIn("preserving axle",why)

    def test_invalid_shapes_and_out_of_range_values_fail_closed(self):
        bads=[{},[],None,"",{"hello":1},json.dumps(self.valid()).replace(
            '"length_mm": 35.0','"length_mm": 50.0')]
        for bad in bads:
            with self.subTest(bad=str(bad)[:40]):
                with self.assertRaises(ValueError):
                    author.parse_model_json(bad if isinstance(bad,str) else json.dumps(bad))

    def test_reference_copy_is_not_claimed_as_new_design(self):
        data=dict(author.REFERENCE,rationale="Keep the old fixture unchanged.")
        with self.assertRaisesRegex(ValueError,"unchanged"):
            author.parse_model_json(json.dumps(data))

    def test_new_candidate_is_written_by_model_not_host(self):
        responses=[(json.dumps(self.valid()),"real/free-model")]
        def request(key,feedback,previous):
            self.assertEqual(key,"fictional")
            self.assertIsNone(feedback)
            return responses.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            result=author.choose(out=folder,key="fictional",request=request)
            self.assertEqual(result["status"],"model_proposed_unverified")
            recorded=json.loads((folder/"proposal.json").read_text())
            self.assertEqual(recorded["design_parameters_mm"]["length_mm"],35.)
            self.assertEqual(result["design_sha256"],
                             author.digest((folder/"proposal.json").read_bytes()))
            self.assertEqual(recorded["model_served"],"real/free-model")

    def test_two_bad_replies_never_invent_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            r=author.choose(out=folder,key="fictional",
                            request=lambda *_: (None,"real/free-model"))
            self.assertEqual(r["status"],"no_candidate")
            self.assertEqual(len(r["attempts"]),2)
            self.assertFalse((folder/"proposal.json").exists())

    def test_no_provider_key_does_not_forge_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            result=author.choose(out=folder,key="")
            self.assertEqual(result["status"],"provider_failure")
            self.assertFalse((folder/"proposal.json").exists())

    def test_second_attempt_receives_separate_qa_rejection(self):
        calls=[]
        def request(key,feedback,previous):
            calls.append((feedback,previous))
            return json.dumps(self.valid()),"real/free"
        with tempfile.TemporaryDirectory() as tmp:
            result=author.choose(out=Path(tmp),key="dummy",
                                 feedback="axle passage blocked",
                                 previous=dict(author.REFERENCE),request=request)
            self.assertEqual(result["status"],"model_proposed_unverified")
            self.assertIn("blocked",calls[0][0])
            self.assertEqual(calls[0][1]["length_mm"],38.0)

    def test_qa_rejects_missing_proposal_and_wrong_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            result=judge.judge(folder/"missing.json",folder/"missing_receipt.json",
                               folder,folder/"qa1")
            self.assertEqual(result["status"],"REJECTED")
            self.assertTrue((folder/"qa1"/"qa.json").is_file())

    def test_qa_rejects_tampered_proposal_before_cad_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            proposal=folder/"proposal.json"
            proposal.write_text(json.dumps({
                "schema":"bean.cad.proposal.v1",
                "design_parameters_mm":self.valid(),
                "rationale":"Minimal material",
                "model_served":"fake"
            }))
            receipt=folder/"author_receipt.json"
            receipt.write_text(json.dumps({
                "schema":"bean.cad.author.v1",
                "status":"model_proposed_unverified",
                "design_sha256":"wronghash",
                "attempts":[{"status":"proposed","model_served":"fake"}]
            }))
            with patch.object(judge,"check_revision",return_value=None):
                result=judge.judge(proposal,receipt,folder,folder/"qa2")
            self.assertEqual(result["status"],"REJECTED")
            self.assertIn("SHA",result["reason"])

    def test_raw_model_response_not_sufficient_to_claim_cad_pass(self):
        class ModelResponse:
            def __enter__(self): return self
            def __exit__(self,*a): return False
            def read(self,*a):
                return json.dumps({"model":"free","choices":[{
                    "message":{"content":json.dumps(self_case.valid())}
                }]}).encode()
        self_case=self
        response, served=author.model_request("fictional",None,None,
                                              opener=lambda *_ ,**kw: ModelResponse())
        self.assertEqual(served,"free")
        self.assertEqual(author.parse_model_json(response)[0]["width_mm"],32.)


if __name__=="__main__":
    unittest.main()
