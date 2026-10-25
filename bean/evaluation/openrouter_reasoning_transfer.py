"""Try BEAN's same real-model task transfer with a pinned FREE reasoning model.

This is an alternate-provider research run, not the blocked GPT-6.1 Sol trial.
It sends only fictional synthetic tasks, not personal or confidential data.
OpenRouter free endpoints may return HTTP 429; no fake successful fallback.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .live_reasoning_transfer import (
    LiveProviderError, OpenAIReasoningModel, canonical, run, SCHEMA,
)

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterFreeReasoner(OpenAIReasoningModel):
    def complete(self, question, context):
        if len(self.calls) >= getattr(self, "call_limit", 18):
            raise LiveProviderError("Fixed real-model request budget exhausted")
        if not isinstance(question, str) or not isinstance(context, str):
            raise TypeError("Question and recalled context must be text")
        instruction = (
            "Solve the following fictional logistics problem using only the "
            "public question and any supplied BEAN lesson. Do not assume an "
            "unknown dispatch protocol is a common standard. If its rule is "
            "not provided and cannot be determined, output UNKNOWN. "
            "Output a single uppercase answer token, nothing else."
        )
        prompt = ("Public question:\n" + question + "\n\n"
                  "Previously recorded BEAN lesson (may be empty or irrelevant):\n"
                  + context.strip())
        payload = {
            "model": self.model_id,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
        }
        req = Request(
            ENDPOINT, method="POST", data=canonical(payload).encode(),
            headers={"Authorization": "Bearer " + self._key,
                     "Content-Type": "application/json",
                     "X-Title": "BEAN Matched Reasoning Study"})
        try:
            with self._request_fn(req, timeout=90) as resp:
                blob = resp.read(500000)
            response = json.loads(blob.decode("utf-8"))
        except HTTPError as exc:
            raise LiveProviderError("OpenRouter HTTP " + str(exc.code)) from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise LiveProviderError("OpenRouter transport/JSON " +
                                    type(exc).__name__) from exc
        if not isinstance(response, dict) or not isinstance(response.get("id"), str):
            raise LiveProviderError("OpenRouter response identifier absent")
        served = str(response.get("model", ""))
        if not served:
            raise LiveProviderError("OpenRouter model identity unverified")
        if self.calls and served != self.calls[0]["model_served"]:
            raise LiveProviderError("Model identity changed during control arms")
        choices = response.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        answer = message.get("content", "")
        if not isinstance(answer, str) or not answer.strip():
            raise LiveProviderError("OpenRouter returned no answer")
        answer = answer.strip()
        if len(answer) > getattr(self, "max_answer_chars", 300):
            raise LiveProviderError("OpenRouter answer exceeds configured safety cap")
        usage = response.get("usage") or {}
        self.calls.append({
            "response_id": response["id"],
            "model_served": served,
            "question_sha256": __import__("hashlib").sha256(question.encode()).hexdigest(),
            "context_sha256": __import__("hashlib").sha256(context.encode()).hexdigest(),
            "answer": answer,
            "usage": {k: usage[k] for k in
                      ("prompt_tokens", "completion_tokens", "total_tokens")
                      if type(usage.get(k)) is int},
        })
        return answer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path("openrouter-free-reasoning"))
    args = p.parse_args()
    try:
        report = run(
            args.output,
            key=os.environ.get("OPENROUTER_API_KEY"),
            model=MODEL,
            model_factory=OpenRouterFreeReasoner)
    except (LiveProviderError, ValueError, AssertionError) as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        report = {"schema": SCHEMA, "status": "blocked_or_failed",
                  "model_requested": MODEL,
                  "error": type(exc).__name__ + ": " + str(exc)[:180],
                  "claim": "No complete OpenRouter real-model holdout evidence"}
        (args.output / "run_status.json").write_text(
            json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("model_calls", "selection_trial",
                                   "holdout_trial", "persisted_decision")},
                     sort_keys=True))
    if report["status"] != "completed_real_provider_trial":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
