"""Offline adversarial protocol tests for the BEAN vs Aider pilot."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from experiments.agent_arena import author, cases, judge


class ArenaProtocolTests(unittest.TestCase):
    def test_original_challenges_genuinely_fail_independent_tests(self):
        for case, spec in cases.CASES.items():
            with self.subTest(case=case):
                outcome = judge.test_source(spec["source"], spec["test"])
                self.assertEqual(outcome["status"], "failed")
                self.assertEqual(outcome["total_tests"], 8)
                self.assertLess(outcome["passed_tests"], 8)

    def test_passing_reference_is_not_supplied_to_agents(self):
        for name in cases.CASES:
            public = cases.public_case(name)
            self.assertEqual(set(public), {"name", "prompt", "source", "source_sha256"})
            self.assertNotIn("test", public)
            self.assertEqual(len(cases.sealed_oracle_digest(name)), 64)

    def test_beans_existing_parser_applies_model_generated_change(self):
        spec = cases.public_case("permission_graph")
        edit = json.dumps({"edits":[{
            "find": "    return False\n",
            "replace": "    return action in grants.get('external', ())\n",
        }]})
        def fake(original, obj, key, feedback=None):
            self.assertEqual(original, spec["source"])
            self.assertEqual(obj["prompt"], spec["prompt"])
            return edit, {"model_served": author.MODEL, "usage": {"total_tokens": 17}}
        result, output = author.bean_author(spec, "fictional-token", model_call=fake)
        self.assertEqual(result["status"], "candidate_drafted_not_tested")
        self.assertEqual(result["usage"]["total_tokens"], 17)
        self.assertIn("external", output)
        self.assertNotEqual(output, spec["source"])

    def test_rejected_model_edit_gets_a_genuine_second_attempt(self):
        attempts = []
        def fake(original, spec, key, feedback=None):
            attempts.append(feedback)
            if not feedback:
                return '{"edits":[]}', {"model_served": author.MODEL}
            return json.dumps({"edits":[{
                "find": "    return False\n",
                "replace": "    return True\n"}]}), {"model_served":author.MODEL}
        receipt, candidate = author.bean_author(
            cases.public_case("permission_graph"), "fictional", model_call=fake)
        self.assertEqual(receipt["status"], "candidate_drafted_not_tested")
        self.assertEqual(len(receipt["attempts"]), 2)
        self.assertIsNone(attempts[0])
        self.assertIn("1 to 5", attempts[1])
        self.assertIn("return True", candidate)

    def test_unchanged_aider_attempt_cannot_be_scored_as_a_fix(self):
        def noop(command, *, cwd, env, capture_output, text, timeout):
            self.assertTrue(any("openrouter/" + author.MODEL == s for s in command))
            self.assertIn("OPENROUTER_API_KEY", env)
            self.assertNotIn("GITHUB_TOKEN", {k: v for k, v in env.items()
                                               if k=="GITHUB_TOKEN" and v=="dummy"})
            self.assertEqual((Path(cwd)/"candidate.py").read_text(),
                             cases.CASES["permission_graph"]["source"])
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        receipt, source = author.aider_author(
            cases.public_case("permission_graph"), "fictional",
            command_runner=noop)
        self.assertEqual(receipt["status"], "no_candidate")
        self.assertIsNone(source)

    def test_no_model_token_never_fabricates_a_patch(self):
        receipt, source = author.bean_author(cases.public_case("permission_graph"), "")
        self.assertEqual(receipt["status"], "provider_failure")
        self.assertIsNone(source)
        receipt2, source2 = author.aider_author(cases.public_case("permission_graph"), "")
        self.assertEqual(receipt2["status"], "provider_failure")
        self.assertIsNone(source2)

    def test_every_agent_and_case_is_written_with_distinct_digest(self):
        with tempfile.TemporaryDirectory() as td:
            def stub(spec, key):
                return ({"status":"candidate_drafted_not_tested", "model_requested":author.MODEL},
                        spec["source"]+"\n# candidate from "+spec["name"]+"\n")
            meta=author.author_all(td, key="fake", bean_writer=stub, aider_writer=stub)
            self.assertEqual(meta["cases_run"], list(cases.CASES))
            for name in cases.CASES:
                for agent in ("bean", "aider"):
                    root=Path(td)/"authors"/agent/name
                    payload=(root/"candidate.py").read_text()
                    receipt=json.loads((root/"receipt.json").read_text())
                    self.assertEqual(receipt["candidate_sha256"], author.sha(payload))

    def test_baseline_green_is_disallowed(self):
        outcome=judge.test_source("def hello(): return 2\n",
                                  "import unittest\nfrom candidate import hello\n"
                                  "class Check(unittest.TestCase):\n"
                                  " def test_ok(self): self.assertEqual(hello(),2)\n")
        self.assertEqual(outcome["status"], "passed")
        self.assertEqual(outcome["passed_tests"], 1)

    def test_manifest_contains_fixed_original_and_oracle_hashes(self):
        manifest=cases.manifest()
        self.assertEqual(set(manifest["case_ids"]),
                         {"ledger_revisions", "permission_graph"})
        for name in manifest["case_ids"]:
            self.assertEqual(manifest["oracle_sha256"][name],
                             cases.sealed_oracle_digest(name))

    def test_no_unseen_tests_in_real_model_prompt(self):
        spec=cases.public_case("permission_graph")
        seen=[]
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, *_):
                return json.dumps({"model":author.MODEL,
                                   "choices":[{"message":{"content":"no plan"}}]}).encode()
        def request(req, timeout):
            seen.append(json.loads(req.data))
            return Response()
        author.bean_model_call(spec["source"], spec, "fictional",
                               request_fn=request)
        text=seen[0]["messages"][1]["content"]
        self.assertIn(spec["prompt"], text)
        self.assertIn(spec["source"], text)
        self.assertNotIn(cases.CASES["permission_graph"]["test"], text)


if __name__ == "__main__":
    unittest.main()
