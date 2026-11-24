import itertools
import operator
import random
import unittest
from bean.learning.constraint_reasoner import solve_constraints


class ConstraintReasoningTests(unittest.TestCase):
    def test_matched_exhaustive_oracle(self):
        rng = random.Random(42177)
        ops = {"eq": operator.eq, "ne": operator.ne, "lt": operator.lt, "ge": operator.ge}
        for _ in range(200):
            domains = {n: rng.sample(range(5), rng.randrange(1, 5)) for n in "abcd"}
            rules = [{"left": rng.choice("abcd"), "right": rng.choice("abcd"),
                      "op": rng.choice(list(ops))} for _ in range(rng.randrange(1, 12))]
            expected = []
            for values in itertools.product(*domains.values()):
                candidate = dict(zip(domains, values))
                if all(ops[r["op"]](candidate[r["left"]], candidate[r["right"]]) for r in rules):
                    expected.append(candidate)
            result = solve_constraints(domains=domains, constraints=rules)
            self.assertEqual(result["verdict"], "unsatisfiable" if not expected else
                             "unique" if len(expected) == 1 else "ambiguous")
            self.assertEqual(len(result["solutions"]), min(len(expected), 2))
            self.assertTrue(all(v in expected for v in result["solutions"]))

    def test_budget_is_not_false_unsat_or_unique(self):
        result = solve_constraints(domains={"a": [1, 2], "b": [3, 4]}, constraints=[], node_limit=1)
        self.assertEqual(result["verdict"], "unknown")
        self.assertTrue(result["budget_exhausted"])

    def test_precedence_and_string_assignment(self):
        result = solve_constraints(domains={"cut": [1], "bend": [1, 2, 3], "inspect": [1, 2, 3]},
            constraints=[{"left": "cut", "op": "lt", "right": "bend"},
                         {"left": "bend", "op": "lt", "right": "inspect"}])
        self.assertEqual(result["solutions"], [{"cut": 1, "bend": 2, "inspect": 3}])
        result = solve_constraints(domains={"a": ["red"], "b": ["red", "blue"]},
            constraints=[{"left": "a", "op": "ne", "right": "b"}])
        self.assertEqual(result["solutions"], [{"a": "red", "b": "blue"}])

    def test_malformed(self):
        with self.assertRaises(ValueError):
            solve_constraints(domains={"a": [1, "x"]}, constraints=[])
        with self.assertRaises(ValueError):
            solve_constraints(domains={"a": [1]}, constraints=[{"left": "a", "op": "exec", "right": "a"}])


if __name__ == "__main__":
    unittest.main()
