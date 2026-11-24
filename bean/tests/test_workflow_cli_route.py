import contextlib
import io
import unittest
from unittest.mock import patch

from bean.runtime.native_orchestration import main


class WorkflowCLIRouteTests(unittest.TestCase):
    def submit(self, extra):
        argv = ["bean", "submit", "Estimate", "--plan-id", "fixed",
                "--inputs", '{"values":[2,7]}'] + extra
        with patch("sys.argv", argv), patch("bean.runtime.inbox.CommandInbox") as inbox:
            with contextlib.redirect_stdout(io.StringIO()):
                main()
            return inbox.return_value.drop.call_args.args

    def test_standard_submission_remains_fresh(self):
        self.assertEqual(self.submit([]), ("cognition_plan", {
            "objective": "Estimate", "inputs": {"values": [2, 7]}, "plan_id": "fixed"}))

    def test_family_selects_memory_first_inbox(self):
        self.assertEqual(self.submit(["--family", "weighted"]), ("cognition_plan_with_memory", {
            "objective": "Estimate", "inputs": {"values": [2, 7]}, "plan_id": "fixed",
            "family": "weighted"}))

    def test_memory_selects_automatic_lookup_without_family(self):
        self.assertEqual(self.submit(["--memory"]), ("cognition_plan_with_memory", {
            "objective": "Estimate", "inputs": {"values": [2, 7]}, "plan_id": "fixed"}))
