import unittest
from bean.runtime.verified_workflows import abstract_args,input_refs

class WorkflowAbstractionTests(unittest.TestCase):
    def test_literals_recover_same_graph(self):
        for x in (3,17):
            args={"values":[x,2*x],"weights":[1,2]}
            self.assertEqual(abstract_args(args["values"],args,[],hint="values"),{"$input":["values"]})
        self.assertEqual(abstract_args(7.5,{"altitude":200},[{"speed":7.5}]),{"$step":0,"path":["speed"]})
    def test_ambiguous_and_unbound_rejected(self):
        for value,inputs in [(7,{"a":7,"b":7}),(9,{"a":7})]:
            with self.assertRaises(ValueError):abstract_args(value,inputs,[])
    def test_exact_explicit_refs(self):
        r={"$step":0,"path":["value"]}
        self.assertEqual(abstract_args(r,{},[]),r)
        self.assertEqual(input_refs(r),0)


from unittest.mock import Mock
from bean.runtime.verified_workflows import VerifiedWorkflows, CAPABILITY
import json


class MemoryFirstTests(unittest.TestCase):
    def setUp(self):
        self.memory=VerifiedWorkflows.__new__(VerifiedWorkflows)
        self.memory.owner=Mock()
        self.memory.store=Mock()
        self.memory.store.fetchone.return_value=None
        self.memory.owner.tools={"retained_weighted_mean":None}
        self.memory.candidates=Mock(return_value=[])
        self.memory.owner.submit.return_value={"status":"pending"}
        self.args={"family":"weighted", "objective":"Compute weighted mean",
                   "inputs":{"values":[3,5],"weights":[2,1]}, "plan_id":"test-1"}

    def test_empty_memory_falls_back_exactly_once(self):
        result=self.memory.plan_with_memory(**self.args)
        self.assertEqual(result["route"],"fresh_fallback")
        self.assertTrue(result["model_invoked"])
        self.memory.owner.submit.assert_called_once_with(
            self.args["objective"],inputs=self.args["inputs"],plan_id="test-1",
            recovery_context={"workflow_family":"weighted",
                              "retained_abstention":"no uniquely verified workflow"})
        self.memory.owner.engine.propose_plan.assert_not_called()

    def test_verified_memory_never_calls_model(self):
        self.memory.candidates.return_value=[{"graph_sha":"test-sha","graph":[
            {"tool":"retained_weighted_mean","args":{"values":{"$input":["values"]},
                                                   "weights":{"$input":["weights"]}}}]}]
        result=self.memory.plan_with_memory(**self.args)
        self.assertEqual(result["route"],"retained")
        self.assertFalse(result["model_invoked"])
        self.memory.owner.submit.assert_not_called()
        self.memory.owner.engine.propose_plan.assert_called_once()

    def test_incompatible_input_fallback_and_strict_abstention(self):
        self.memory.candidates.return_value=[{"graph_sha":"test-sha","graph":[
            {"tool":"retained_weighted_mean","args":{"values":{"$input":["missing"]}}}]}]
        strict=self.memory.reuse(family="weighted",inputs=self.args["inputs"],plan_id="strict")
        self.assertEqual(strict["status"],"abstain")
        self.memory.owner.submit.assert_not_called()
        result=self.memory.plan_with_memory(**self.args)
        self.assertEqual(result["route"],"fresh_fallback")
        self.assertEqual(result["retained_abstention"],"retained input binding incompatible")
        self.memory.owner.engine.propose_plan.assert_not_called()
        self.memory.owner.submit.assert_called_once()

    def test_existing_plan_is_not_submitted_again(self):
        self.memory.store.fetchone.return_value={"action_detail":json.dumps({
            "capability":CAPABILITY,"objective":self.args["objective"],
            "inputs":self.args["inputs"],"workflow_family":"weighted"})}
        self.assertEqual(self.memory.plan_with_memory(**self.args)["route"],"existing")
        self.memory.owner.submit.assert_not_called()
        self.memory.owner.engine.propose_plan.assert_not_called()
        with self.assertRaises(ValueError):
            self.memory.plan_with_memory(**dict(self.args,family="other"))

    def test_proposal_failure_does_not_submit_second_plan(self):
        self.memory.candidates.return_value=[{"graph_sha":"test-sha","graph":[
            {"tool":"retained_weighted_mean","args":{"values":{"$input":["values"]}}}]}]
        self.memory.owner.engine.propose_plan.side_effect=RuntimeError("write failure")
        with self.assertRaises(RuntimeError):
            self.memory.plan_with_memory(**self.args)
        self.memory.owner.submit.assert_not_called()
