"""Supervisor-side workflow validation client regression tests."""
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from bean.runtime import workflow_validation_cli as cli


def case():
    return {"family": "synthetic", "graph_sha": "a" * 64, "inputs": {"x": 8},
            "checks": [{"step": 0, "path": ["value"], "expected": 16}],
            "evidence_ref": "independent-fixture-v1"}


class ValidationClientTests(unittest.TestCase):
    def test_id_is_stable_and_oracle_cannot_manufacture_new_trial(self):
        a = case()
        b = case()
        b["checks"][0]["expected"] = 17
        self.assertEqual(cli.replay_id(a), cli.replay_id(b))
        b["inputs"]["x"] = 9
        self.assertNotEqual(cli.replay_id(a), cli.replay_id(b))

    def test_invalid_check_and_nonfinite_input_rejected(self):
        a = case()
        a["checks"][0]["step"] = True
        with self.assertRaises(ValueError):
            cli.validate_case(a)
        a = case()
        a["inputs"]["x"] = float("nan")
        with self.assertRaises(ValueError):
            cli.validate_case(a)

    def test_processed_abstention_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "processed").mkdir()
            path = root / "command.json"
            (root / "processed" / path.name).touch()
            with self.assertRaisesRegex(RuntimeError, "without a durable result"):
                cli.await_observation(lambda: None, path, time.monotonic() + 1, .01)

    def test_processed_nonterminal_plan_can_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "processed").mkdir()
            path = root / "command.json"
            (root / "processed" / path.name).touch()
            states = iter([{"status": "running"}, {"status": "completed"}])
            result = cli.await_observation(lambda: next(states), path,
                time.monotonic() + 1, .001,
                terminal=lambda x: x["status"] == "completed")
            self.assertEqual(result["status"], "completed")

    def test_real_sqlite_evidence_reconnect_and_changed_oracle_rejected(self):
        a = case()
        pid = cli.replay_id(a)
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "core.sqlite"
            conn = sqlite3.connect(database)
            conn.executescript("""
                CREATE TABLE cognition_goal_proposals(proposal_id TEXT, action_detail TEXT);
                CREATE TABLE bean_verified_workflow_trials(plan_id TEXT, family TEXT,
                    graph_sha TEXT, input_sha TEXT, evidence_json TEXT, passed INTEGER);
            """)
            conn.execute("INSERT INTO cognition_goal_proposals VALUES (?,?)",
                (cli.plan_proposal_id(pid, 0), json.dumps({"workflow_sha": a["graph_sha"],
                "inputs": a["inputs"], "planner_provider": "candidate_validation"})))
            evidence = {"source": a["evidence_ref"],
                        "checks": [{**a["checks"][0], "actual": 16, "matched": True}]}
            conn.execute("INSERT INTO bean_verified_workflow_trials VALUES (?,?,?,?,?,?)",
                (pid, a["family"], a["graph_sha"], "input-sha", json.dumps(evidence), 1))
            conn.commit()
            conn.close()
            with patch.object(cli, "CommandInbox") as inbox:
                result = cli.run_case(database, Path(tmp) / "inbox", a)
                self.assertTrue(result["reconnected"])
                self.assertEqual(result["trial"]["passed"], 1)
                inbox.assert_not_called()
                a["checks"][0]["expected"] = 17
                with self.assertRaisesRegex(ValueError, "immutable"):
                    cli.run_case(database, Path(tmp) / "inbox", a)


if __name__ == "__main__":
    unittest.main()
