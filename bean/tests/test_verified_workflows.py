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
