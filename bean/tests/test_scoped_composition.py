import unittest
from types import SimpleNamespace
from bean.learning.composition import CompositionLearner

class ScopedCompositionTests(unittest.TestCase):
    def test_large_journal_and_exact_dedup(self):
        rules=[dict(rule_id=str(i),domain="domain-"+str(i),grammar="tags",operation="digit_desc") for i in range(100)]
        rules += [dict(rule_id="duplicate",domain="domain-0",grammar="tags",operation="digit_desc"),
                  dict(rule_id="g",domain="gauge",grammar="gauge",operation="minimum")]
        bank=SimpleNamespace(journal=SimpleNamespace(events=lambda:[{"kind":"local_rule","data":r} for r in rules]))
        learner=CompositionLearner(bank)
        with self.assertRaises(ValueError):learner._parents()
        self.assertEqual([r["rule_id"] for r in learner._parents({"tags"},["domain-0","domain-1"])],["0","1"])
        self.assertEqual([r["rule_id"] for r in learner._parents({"gauge"})],["g"])
    def test_invalid_scope(self):
        learner=CompositionLearner(SimpleNamespace(journal=SimpleNamespace(events=lambda:[])))
        with self.assertRaises(ValueError):learner._parents(parent_domains="domain")
