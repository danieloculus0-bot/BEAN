"""Bounded REAL reasoning-model test of BEAN-native retained lessons.

No actual source-code or trading execution. A single pinned OpenAI reasoning model
sees the same public tasks with cold, placebo, and BEAN-native lesson contexts.
Expected answers are passed only to a deterministic judge, never the model.
The model remains frozen; only BEAN's source-linked experience journal changes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bean.learning import BEANReasoningSkills, ExperienceBank, TrialCase

MODEL = "gpt-6.1-sol"
ENDPOINT = "https://api.openai.com/v1/responses"
SCHEMA = "bean.native.real_reasoning_transfer.v1"
RULE = (
    "ASTER-7 dispatch key procedure: read each capital-letter and single-digit "
    "tag pair, order the tag pairs by their numeric digits ASCENDING, then join "
    "their capital letters WITHOUT spaces or separators. Return only that key."
)
DEVELOPMENT = TrialCase(
    "development-origin", "aster-routing",
    "ASTER-7 dispatch key for tags N9 C2 Y6. Output one key.", "CYN")
SELECTION = (
    TrialCase("selection-1", "aster-routing",
              "ASTER-7 dispatch key for tags P8 D3 T6. Output one key.", "DTP"),
    TrialCase("selection-2", "aster-routing",
              "ASTER-7 dispatch key for tags L5 V1 S9. Output one key.", "VLS"),
)
HOLDOUT = (
    TrialCase("holdout-1", "aster-routing",
              "ASTER-7 dispatch key for tags W7 B4 Q2. Output one key.", "QBW"),
    TrialCase("holdout-2", "aster-routing",
              "ASTER-7 dispatch key for tags G6 X2 A8. Output one key.", "XGA"),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def verdict(expected, observed):
    return observed.strip() == expected


class LiveProviderError(RuntimeError):
    """No fake model answers or silent simulated fallback."""


class OpenAIReasoningModel:
    provider_kind = "real_model"

    def __init__(self, key, *, model=MODEL, request_fn=urlopen):
        if not key or not isinstance(key, str):
            raise LiveProviderError("OPENAI_API_KEY unavailable")
        if not isinstance(model, str) or not model:
            raise ValueError("Model ID required")
        self.model_id = model
        self._key = key
        self._request_fn = request_fn
        self.calls = []

    def complete(self, question, context):
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
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 2048,
            "tool_choice": "none",
            "input": [
                {"role": "developer", "content": instruction},
                {"role": "user", "content": prompt},
            ],
        }
        req = Request(
            ENDPOINT, method="POST", data=canonical(payload).encode(),
            headers={"Authorization": "Bearer " + self._key,
                     "Content-Type": "application/json"})
        try:
            with self._request_fn(req, timeout=90) as resp:
                blob = resp.read(500000)
            response = json.loads(blob.decode("utf-8"))
        except HTTPError as exc:
            # Never print the service response body or bearer credential.
            raise LiveProviderError("OpenAI HTTP " + str(exc.code)) from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise LiveProviderError("OpenAI transport/JSON " +
                                    type(exc).__name__) from exc
        if not isinstance(response, dict) or not isinstance(response.get("id"), str):
            raise LiveProviderError("OpenAI response identifier absent")
        served = str(response.get("model", ""))
        if not served:
            raise LiveProviderError("OpenAI served model unverified")
        if self.calls and served != self.calls[0]["model_served"]:
            raise LiveProviderError("Model changed midway through paired trial")
        output = []
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    output.append(part["text"])
        answer = "".join(output).strip()
        if not answer:
            raise LiveProviderError("OpenAI returned no visible answer")
        if len(answer) > 300:
            raise LiveProviderError("OpenAI returned excessive answer text")
        usage = response.get("usage") or {}
        self.calls.append({
            "response_id": response["id"],
            "model_served": served,
            "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
            "context_sha256": hashlib.sha256(context.encode()).hexdigest(),
            "answer": answer,
            "usage": {k: usage[k] for k in
                      ("input_tokens", "output_tokens", "total_tokens")
                      if type(usage.get(k)) is int},
        })
        return answer


def run(output, *, key=None, model=MODEL, model_factory=OpenAIReasoningModel):
    """One real, bounded study; writes receipts even when evidence disappoints."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError("Refuse to overwrite an earlier research study")
    if not key:
        report = {"schema": SCHEMA, "status": "blocked_no_api_key",
                  "model_requested": model, "requests": 0,
                  "claim": "NO real reasoning model was tested"}
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    provider = model_factory(key, model=model)
    bank = ExperienceBank(output / "experience.sqlite3")
    try:
        bean = BEANReasoningSkills(bank)
        # The development mismatch is the real model's answer, not a scripted
        # mistake. The public task's correct key is visible only to the judge.
        raw = provider.complete(DEVELOPMENT.public_question, "")
        if verdict(DEVELOPMENT.expected, raw):
            raise LiveProviderError(
                "Development control unexpectedly correct; no demonstrated error to learn")
        bean.reflect(
            domain=DEVELOPMENT.domain, task_id=DEVELOPMENT.task_id,
            observed=raw, expected=DEVELOPMENT.expected,
            adjustment_hypothesis=RULE,
            evidence_refs=["development:" + digest(
                [DEVELOPMENT.public_question, raw, DEVELOPMENT.expected])])
        # Never mark a reusable skill as successful without an actual observed
        # developer-period model trial, measured against the same rule.
        trial_skill = provider.complete(DEVELOPMENT.public_question, RULE)
        if not verdict(DEVELOPMENT.expected, trial_skill):
            raise LiveProviderError(
                "Development instruction not verified; cannot retain a passed skill")
        bean.retain_skill(
            domain=DEVELOPMENT.domain, name="ASTER-7 dispatch",
            steps=[RULE], passed=True,
            evidence_refs=["development:verified_skill:" +
                           digest([DEVELOPMENT.public_question, trial_skill])])
        bean.propose_instruction(
            domain=DEVELOPMENT.domain, instruction=RULE,
            evidence_refs=["development:hypothesis:" + digest(RULE)])
        bean.reflect(
            domain="unrelated-calibration", task_id="unrelated",
            observed="red", expected="blue",
            adjustment_hypothesis="unrelated color comparison",
            evidence_refs=["fixture:unrelated-placebo"])
        selected = bean.evaluate_and_select(
            domain=DEVELOPMENT.domain, cases=SELECTION,
            model=provider, judge=verdict, replicates=1)
        # Close and recover from SQLite before any holdout model calls.
        chosen = selected["selection"]["arm"]
        source_tip = bank.journal.events()[-1]
        bank.close()
        bank = ExperienceBank(output / "experience.sqlite3")
        bean = BEANReasoningSkills(bank)
        restart = bean.decide(
            domain=DEVELOPMENT.domain, task_ref="restart-check",
            query=HOLDOUT[0].public_question)
        if restart["selected_strategy"] != chosen:
            raise AssertionError("Frozen strategy changed after restart")
        holdout = bean.evaluate_holdout(
            domain=DEVELOPMENT.domain, cases=HOLDOUT,
            model=provider, judge=verdict, replicates=1)
        # Keep every model reply, not only summary scores. The model may be
        # wrong even when source data and persistence machinery are correct.
        score = holdout["trial"]["scores"]
        report = {
            "schema": SCHEMA, "status": "completed_real_provider_trial",
            "model_requested": model,
            "model_served": provider.calls[0]["model_served"],
            "provider_kind": provider.provider_kind,
            "requests": len(provider.calls),
            "selection": selected["selection"],
            "selection_trial": selected["trial"],
            "holdout_trial": holdout["trial"],
            "persisted_decision": restart,
            "restart_selection_identical": restart["selected_strategy"] == chosen,
            "source_tip_record_kind": source_tip["kind"],
            "model_calls": provider.calls,
            "holdout_increment_over_cold": score["adaptive"] - score["cold"],
            "holdout_increment_over_placebo": score["adaptive"] - score["placebo"],
            "weight_learning": False,
            "independent_blindness_authenticated": False,
            "interpretation": (
                "Same real reasoning model + BEAN source-linked, retained "
                "context. Synthetic invented task family and evaluator-authored "
                "feedback; does not prove independent real-world reasoning, "
                "neural weight change, causal understanding or trading profit."
            ),
        }
        (output / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n")
        return report
    finally:
        bank.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("real-reasoner-results"))
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    try:
        report = run(args.output, key=os.environ.get("OPENAI_API_KEY"),
                     model=args.model)
    except (LiveProviderError, ValueError, AssertionError) as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        # A reason, rather than a fake experiment result.
        report = {"schema": SCHEMA, "status": "blocked_or_failed",
                  "model_requested": args.model,
                  "error": type(exc).__name__ + ": " + str(exc)[:180],
                  "claim": "No complete real-model matched holdout evidence"}
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
