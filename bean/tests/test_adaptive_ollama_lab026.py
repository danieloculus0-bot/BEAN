"""Controlled adapter trials with BEAN's real optional local Ollama API."""
import json
import unittest

from bean.learning.model_adapters import LocalOllamaTrialModel


class FakeClient:
    def __init__(self):
        self.calls=[]
    def chat_json(self,model,messages,schema=None):
        self.calls.append((model,messages,schema))
        return json.dumps({"answer":"42"})


class LocalModelAdapterTests(unittest.TestCase):
    def test_model_identity_same_across_contexts_and_no_answer_key(self):
        fake=FakeClient()
        runner=LocalOllamaTrialModel("qwen2.5-coder:1.5b",client=fake)
        self.assertEqual(runner.complete("Solve 6*7",""),"42")
        self.assertEqual(runner.complete("Solve 6*7","Prior context"),"42")
        self.assertEqual(runner.model_id,"ollama:qwen2.5-coder:1.5b")
        self.assertTrue(all(x[0]=="qwen2.5-coder:1.5b" for x in fake.calls))
        self.assertTrue(all("Prior experimental context" in x[1][1]["content"] for x in fake.calls))
        self.assertTrue(all(x[2]["required"]==["answer"] for x in fake.calls))

    def test_refuses_unstructured_or_fake_model_output(self):
        class FakeBad:
            def chat_json(self,*args,**kwargs):
                return '{"summary":"not an answer"}'
        with self.assertRaises(ValueError):
            LocalOllamaTrialModel(client=FakeBad()).complete("Question","")


if __name__=="__main__":
    unittest.main()
