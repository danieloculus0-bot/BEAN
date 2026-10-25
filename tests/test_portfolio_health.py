"""Offline tests for GitHub portfolio evidence; no network or credentials needed."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "portfolio_health.py"
spec = importlib.util.spec_from_file_location("portfolio_health", SCRIPT)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class PortfolioHealthTests(unittest.TestCase):
    def test_empty_checks_are_unknown(self):
        self.assertEqual(health.summarize_checks([])["status"], "unknown")

    def test_failed_check_outweighs_success_and_pending(self):
        checks = [
            {"status": "completed", "conclusion": "success"},
            {"status": "completed", "conclusion": "failure"},
            {"status": "queued", "conclusion": None},
        ]
        x = health.summarize_checks(checks)
        self.assertEqual((x["status"], x["passed"], x["failed"], x["pending"]), ("failed", 1, 1, 1))

    def test_pending_is_not_success(self):
        self.assertEqual(
            health.summarize_checks([{"status": "in_progress", "conclusion": None}])["status"],
            "pending",
        )

    def test_public_inventory_exact_head_and_prs(self):
        seen = []

        def fake_request(path):
            seen.append(path)
            if path.startswith("/users/"):
                return [
                    {
                        "name": "alpha", "html_url": "https://github.com/example/alpha",
                        "owner": {"login": "example"}, "default_branch": "main", "archived": False,
                    },
                    {
                        "name": "not-owned", "html_url": "https://github.com/elsewhere/not-owned",
                        "owner": {"login": "elsewhere"}, "default_branch": "main",
                    },
                ]
            if path.endswith("/branches/main"):
                return {"commit": {"sha": "a" * 40}}
            if "/check-runs?" in path:
                return {"total_count": 1, "check_runs": [{"status": "completed", "conclusion": "success"}]}
            if "/pulls?" in path:
                return [{"number": 13}, {"number": 14}]
            raise AssertionError(path)

        report = health.collect("example", fake_request)
        self.assertEqual(len(report["repos"]), 1)
        row = report["repos"][0]
        self.assertEqual(row["head_sha"], "a" * 40)
        self.assertEqual(row["ci"]["status"], "passed")
        self.assertEqual(row["open_prs"], "2")
        self.assertTrue(any("/commits/" + "a" * 40 + "/check-runs?" in p for p in seen))
        self.assertIn("passing check does not prove full runtime functionality".lower(),
                      health.markdown(report).lower())

    def test_partial_errors_are_explicit_not_green(self):
        def fake_request(path):
            if path.startswith("/users/"):
                return [{
                    "name": "r", "owner": {"login": "example"},
                    "default_branch": "main", "html_url": "https://github.com/example/r",
                }]
            if "/branches/" in path:
                raise OSError("offline")
            if "/pulls?" in path:
                return []
            raise AssertionError(path)

        row = health.collect("example", fake_request)["repos"][0]
        self.assertEqual(row["ci"]["status"], "unknown")
        self.assertTrue(row["errors"])
        self.assertEqual(row["open_prs"], "0")

    def test_truncated_checks_mark_incomplete(self):
        def fake_request(path):
            if path.startswith("/users/"):
                return [{
                    "name": "r", "owner": {"login": "example"},
                    "default_branch": "main", "html_url": "https://github.com/example/r",
                }]
            if "/branches/" in path:
                return {"commit": {"sha": "b" * 40}}
            if "/check-runs?" in path:
                return {"total_count": 101, "check_runs": [{"status": "completed", "conclusion": "success"}]}
            if "/pulls?" in path:
                return []
            raise AssertionError(path)

        row = health.collect("example", fake_request)["repos"][0]
        self.assertEqual(row["ci"]["status"], "incomplete")
        self.assertTrue(row["errors"])


if __name__ == "__main__":
    unittest.main()
