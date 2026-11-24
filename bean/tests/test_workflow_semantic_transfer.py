import json
import sqlite3
import unittest

from bean.runtime.workflow_discovery import input_shape, transfer_candidates, select_transfer


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
          CREATE TABLE bean_verified_workflow_trials
            (family TEXT, plan_id TEXT, graph_sha TEXT, passed INTEGER);
          CREATE TABLE cognition_goal_proposals (action_detail TEXT, status TEXT);
        """)
        self.graphs = {}
        self.inputs = {"values": [1, 3], "weights": [1, 2]}

    def tearDown(self):
        self.db.close()

    def add(self, family, objective, tool, *, verified=True, provider="local_llamacpp"):
        pid = family
        graph = {"graph_sha": family, "graph": [{"tool": tool, "args": {}}]}
        self.graphs[family] = [graph] if verified else []
        self.db.execute("INSERT INTO bean_verified_workflow_trials VALUES (?,?,?,1)",
                        (family, pid, family))
        self.db.execute("INSERT INTO cognition_goal_proposals VALUES (?,?)",
            (json.dumps({"goal_plan":{"id":pid,"step":0},
             "capability":"native_orchestration_step", "objective":objective,
             "inputs":self.inputs,"planner_provider":provider}), "completed"))

    def options(self, inputs=None):
        return transfer_candidates(self.db, self.inputs if inputs is None else inputs,
                                   lambda family: self.graphs[family])

    def test_shape_matches_new_numeric_values_and_lengths(self):
        self.add("mean", "Compute weighted average", "weighted_mean")
        options = self.options({"weights":[1.5, 2, 3], "values":[5, 6, 8]})
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["family"], "mean")
        self.assertNotIn("inputs", options[0])
        self.assertEqual(self.options({"values":[True], "weights":[2]}), [])

    def test_unverified_and_replayed_procedures_not_candidates(self):
        self.add("unverified", "average", "weighted_mean", verified=False)
        self.add("replayed", "average", "weighted_mean", provider="semantic_workflow")
        self.assertEqual(self.options(), [])

    def test_similar_input_structure_does_not_automatically_select(self):
        self.add("mean", "Compute weighted average", "weighted_mean")
        self.add("sum", "Compute weighted sum", "weighted_sum")
        prompts = []
        def reject(prompt):
            prompts.append(prompt)
            return '{"candidate":null}', "model", "local"
        self.assertIsNone(select_transfer("Find the median", self.inputs, self.options(), reject))
        self.assertIn("weighted_mean", prompts[0])
        self.assertIn("weighted_sum", prompts[0])

    def test_paraphrase_selects_only_model_chosen_graph(self):
        self.add("mean", "Compute weighted average", "weighted_mean")
        self.add("sum", "Compute weighted sum", "weighted_sum")
        choice = select_transfer("Estimate using relative reliability", self.inputs,
                                 self.options(), lambda p: ('{"candidate":0}', "qwen", "local"))
        self.assertEqual(choice["family"], "mean")
        self.assertEqual(choice["model"], "qwen")

    def test_malformed_and_out_of_range_decisions_abstain(self):
        self.add("mean", "Compute weighted average", "weighted_mean")
        for raw in ('bad', '{"candidate":true}', '{"candidate":-1}',
                    '{"candidate":1}', '{"candidate":0,"other":1}', '[]'):
            self.assertIsNone(select_transfer("Average", self.inputs, self.options(),
                                              lambda p: (raw, "model", "local")))

    def test_overflow_does_not_hide_competing_candidates(self):
        for i in range(9):
            self.add(str(i), "Compute something", "tool")
        self.assertEqual(self.options(), [])

    def test_no_options_means_no_model_call(self):
        def ask(prompt):
            self.fail("model called with no candidates")
        self.assertIsNone(select_transfer("New task", self.inputs, [], ask))

    def test_selector_receives_current_conditions_and_relevant_contracts(self):
        self.add("mean", "Compute weighted average", "weighted_mean")
        observed = []
        def ask(prompt):
            observed.append(json.loads(prompt.split("\n", 1)[1]))
            return '{"candidate":0}', "model", "local"
        current = {"values":[99, 200, 301], "weights":[3, 4, 5]}
        select_transfer("Estimate", current, self.options(current), ask,
                        tool_descriptions={"weighted_mean":"weighted estimate",
                                           "unrelated":"unrelated action"})
        self.assertEqual(observed[0]["current_inputs"], current)
        self.assertEqual(observed[0]["tool_contracts"], {"weighted_mean":"weighted estimate"})
        self.assertNotIn("inputs", observed[0]["candidates"][0])
