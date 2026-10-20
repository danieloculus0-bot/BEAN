"""Opt-in local language-model test adapter for Lab026.

Uses the installed BEAN Ollama transport. All arms use identical provider,
model, structured-output schema and generation settings. Model weights are
unchanged. The model is never given sealed evaluator truth.
"""
from __future__ import annotations
import json
from bean.voice.ollama import OllamaClient


ANSWER_SCHEMA={
    "type":"object","properties":{"answer":{"type":"string"}},
    "required":["answer"],"additionalProperties":False,
}


class LocalOllamaTrialModel:
    provider_kind="real_model"

    def __init__(self,model_name="qwen2.5-coder:1.5b",client=None):
        if not isinstance(model_name,str) or not model_name.strip():
            raise ValueError("Explicit installed model name required")
        self.model_name=model_name
        self.model_id="ollama:"+model_name
        self.client=client if client is not None else OllamaClient()

    def complete(self,question,context):
        prompt=("Solve the user's task. Output only JSON with one key named answer. "
                "When context is supplied, it may contain hypotheses or prior "
                "experiences, NOT automatically verified rules. "
                "Consider but do not blindly trust it.")
        data=[
            {"role":"system","content":prompt},
            {"role":"user","content":"Task:\n"+question+"\n\nPrior experimental context:\n"+context},
        ]
        raw=self.client.chat_json(self.model_name,data,schema=ANSWER_SCHEMA)
        parsed=json.loads(raw)
        if not isinstance(parsed,dict) or set(parsed)!={"answer"} or \
           not isinstance(parsed["answer"],str):
            raise ValueError("Unusable Ollama answer schema")
        return parsed["answer"]
