"""Credential-free tests of BEAN's *generic* retry strategy after a rejected edit.

The tests never contain reference solutions for the actual arena problems.
Model code comes solely from fake API replies, then faces the existing gates.
"""
from __future__ import annotations
import json
import unittest
from experiments.agent_arena import author, cases


class AdaptiveAuthorTests(unittest.TestCase):
    def test_second_empty_reply_uses_different_output_format(self):
        spec = cases.public_case("permission_graph")
        requests = []
        class Reply:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, *_):
                return json.dumps({
                    "model": author.MODEL,
                    "choices": [{"message": {"content": None},
                                 "finish_reason": "stop"}],
                }).encode()
        def fake(req, timeout):
            requests.append(json.loads(req.data))
            return Reply()
        author.bean_model_call(spec["source"], spec, "fictional",
                               request_fn=fake)
        author.bean_model_call(spec["source"], spec, "fictional",
                               request_fn=fake,
                               feedback="ValueError: model reply contained no edit text")
        self.assertEqual(len(requests), 2)
        first = requests[0]["messages"][1]["content"]
        second = requests[1]["messages"][1]["content"]
        self.assertIn("Return ONLY JSON", first)
        self.assertIn("COMPLETE runnable replacement", second)
        self.assertNotIn("Return ONLY JSON", second)
        self.assertEqual(requests[0]["model"], requests[1]["model"])
        self.assertEqual(requests[0]["max_tokens"], 2800)
        self.assertEqual(requests[1]["max_tokens"], 5000)
        self.assertNotIn(cases.CASES["permission_graph"]["test"], first)
        self.assertNotIn(cases.CASES["permission_graph"]["test"], second)

    def test_complete_model_source_is_not_a_hardcoded_solution(self):
        original = "def work(x):\n    return x\n"
        model_reply = "def work(x):\n    return x + 3\n"
        output, changes = author.model_written_module(original, model_reply)
        self.assertEqual(output, model_reply)
        self.assertGreater(changes, 0)
        self.assertNotEqual(author.sha(original), author.sha(output))

    def test_second_trial_model_authored_source_is_accepted_with_metadata(self):
        spec = cases.public_case("permission_graph")
        original = spec["source"]
        changed = original.replace("return False", "return bool(action == 'synthetic')")
        trials = []
        def model_call(source, scenario, key, feedback=None):
            trials.append(feedback)
            return (None if not feedback else changed), {
                "model_served": author.MODEL, "usage": {"total_tokens": 80}
            }
        result, candidate = author.bean_author(spec, "dummy", model_call=model_call)
        self.assertEqual(candidate, changed)
        self.assertEqual(result["status"], "candidate_drafted_not_tested")
        self.assertEqual(len(trials), 2)
        self.assertEqual(result["attempts"][0]["status"], "invalid_candidate")
        self.assertFalse(result["attempts"][0]["reply_has_text"])
        self.assertEqual(result["attempts"][1]["output_format"], "whole_python")
        self.assertEqual(result["usage"]["total_tokens"], 160)
        self.assertEqual(result["candidate_sha256"], author.sha(changed))

    def test_fenced_python_model_response_is_supported_without_shell_actions(self):
        original = "def public_api(x):\n    return x\n"
        fence = chr(96)*3
        fenced = (fence + "python\n"
                  "def public_api(x):\n    return x * 2\n"
                  + fence)
        out, _ = author.model_written_module(original, fenced)
        self.assertEqual(out, "def public_api(x):\n    return x * 2\n")

    def test_prose_or_json_disguised_as_source_does_not_count(self):
        orig = "def public_api(x):\n    return x\n"
        for body in ('{"edits":[{"find":"x","replace":"y"}]}',
                     "I think you can optimize it by caching",
                     "print('hi')", "", None):
            with self.subTest(body=body):
                with self.assertRaises((ValueError, SyntaxError)):
                    author.model_written_module(orig, body)

    def test_preserves_original_public_signature_and_rejects_no_op(self):
        original = "def compute(a, b):\n    return a + b\n"
        for source in ("def compute(a):\n    return a + 1\n",
                       "def unrelated(a, b):\n    return a + b\n",
                       original):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    author.model_written_module(original, source)

    def test_invalid_full_module_is_not_marked_success(self):
        spec = cases.public_case("permission_graph")
        def model_call(original, scenario, key, feedback=None):
            return (None if not feedback else
                    "def can_access(user, action, memberships, grants, denies):\n"
                    "    return ("), {
                "model_served": author.MODEL
            }
        result, candidate = author.bean_author(spec, "fictional",
                                               model_call=model_call)
        self.assertIsNone(candidate)
        self.assertEqual(result["status"], "no_candidate")
        self.assertEqual(len(result["attempts"]), 2)
        self.assertTrue(all(x["status"] == "invalid_candidate"
                            for x in result["attempts"]))


if __name__ == "__main__":
    unittest.main()
