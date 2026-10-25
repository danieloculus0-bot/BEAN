"""BEAN Lab028: actual Nemotron model-authored lessons, two unrelated rule families.

The provider sees public development demonstrations but never heldout answers.
BEAN stores actual model-authored reflection, independently tests it on a
development validation question, selects among matched strategies and evaluates
the frozen strategy after SQLite restart on disjoint questions. Bad outcomes are
evidence: no hardcoded success flags, deterministic stand-in, order retries or
paid-model fallback. This is research, NOT live trading or general AI proof.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request

from bean.learning import BEANReasoningSkills, ExperienceBank, TrialCase
from bean.evaluation.live_reasoning_transfer import LiveProviderError, canonical
from bean.evaluation.openrouter_reasoning_transfer import (
    OpenRouterFreeReasoner, MODEL, ENDPOINT
)

SCHEMA = "bean.nemotron.self_derived_transfer.v1"
MAX_CALLS = 50

@dataclass(frozen=True)
class Domain:
    name: str
    demonstrations: tuple[TrialCase, ...]
    validation: TrialCase
    selection: tuple[TrialCase, ...]
    holdout: tuple[TrialCase, ...]


DOMAINS = (
    Domain(
        "orchid-routing",
        (
            TrialCase("orchid-dev-1", "orchid-routing",
                      "ORCHID-7 for tags K2 P8 D5. Return key.", "PDK"),
            TrialCase("orchid-dev-2", "orchid-routing",
                      "ORCHID-7 for tags R4 M9 J1. Return key.", "MRJ"),
            TrialCase("orchid-dev-3", "orchid-routing",
                      "ORCHID-7 for tags B3 W6 H8. Return key.", "HWB"),
        ),
        TrialCase("orchid-validate", "orchid-routing",
                  "ORCHID-7 for tags T7 A2 F9. Return key.", "FTA"),
        (
            TrialCase("orchid-select-a", "orchid-routing",
                      "ORCHID-7 for tags N5 C9 L1. Return key.", "CNL"),
            TrialCase("orchid-select-b", "orchid-routing",
                      "ORCHID-7 for tags Y2 E7 S4. Return key.", "ESY"),
        ),
        (
            TrialCase("orchid-holdout-1", "orchid-routing",
                      "ORCHID-7 for tags V8 B3 Q6. Return key.", "VQB"),
            TrialCase("orchid-holdout-2", "orchid-routing",
                      "ORCHID-7 for tags R1 G9 J5. Return key.", "GJR"),
            TrialCase("orchid-holdout-3", "orchid-routing",
                      "ORCHID-7 for tags X4 C7 P2. Return key.", "CXP"),
            TrialCase("orchid-holdout-4", "orchid-routing",
                      "ORCHID-7 for tags L6 T3 D8. Return key.", "DLT"),
        ),
    ),
    Domain(
        "harbor-gauges",
        (
            TrialCase("harbor-dev-1", "harbor-gauges",
                      "HARBOR-4 for gauges A=9 B=3 C=6. Return label.", "C"),
            TrialCase("harbor-dev-2", "harbor-gauges",
                      "HARBOR-4 for gauges D=14 E=20 F=7. Return label.", "D"),
            TrialCase("harbor-dev-3", "harbor-gauges",
                      "HARBOR-4 for gauges G=4 H=1 J=10. Return label.", "G"),
        ),
        TrialCase("harbor-validate", "harbor-gauges",
                  "HARBOR-4 for gauges K=19 L=8 M=13. Return label.", "M"),
        (
            TrialCase("harbor-select-a", "harbor-gauges",
                      "HARBOR-4 for gauges P=6 Q=15 R=10. Return label.", "R"),
            TrialCase("harbor-select-b", "harbor-gauges",
                      "HARBOR-4 for gauges T=21 U=12 V=17. Return label.", "V"),
        ),
        (
            TrialCase("harbor-holdout-1", "harbor-gauges",
                      "HARBOR-4 for gauges A=5 B=11 C=8. Return label.", "C"),
            TrialCase("harbor-holdout-2", "harbor-gauges",
                      "HARBOR-4 for gauges D=18 E=14 F=3. Return label.", "E"),
            TrialCase("harbor-holdout-3", "harbor-gauges",
                      "HARBOR-4 for gauges G=2 H=7 J=4. Return label.", "J"),
            TrialCase("harbor-holdout-4", "harbor-gauges",
                      "HARBOR-4 for gauges K=20 L=9 M=13. Return label.", "M"),
        ),
    )
)


def correct(expected, actual):
    return actual.strip().upper() == expected


def task_fingerprints():
    from bean.learning.experimental import question_fingerprint
    original = [case for domain in DOMAINS for case in (
        *domain.demonstrations, domain.validation,
        *domain.selection, *domain.holdout)]
    if len({x.task_id for x in original}) != len(original):
        raise ValueError("Duplicated task IDs")
    if len({question_fingerprint(x.public_question) for x in original}) != len(original):
        raise ValueError("Duplicated development/selection/holdout question")
    if not all(x.domain == domain.name for domain in DOMAINS for x in (
        *domain.demonstrations, domain.validation,
        *domain.selection, *domain.holdout)):
        raise ValueError("Incorrect test domain")
    return original


class RecordingNemotron(OpenRouterFreeReasoner):
    """Same pinned real model for all trials; append each answer durably."""

    def __init__(self, key, *, model=MODEL, output, request_fn=None):
        kw = {"model": model}
        if request_fn is not None:
            kw["request_fn"] = request_fn
        super().__init__(key, **kw)
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.progress_path = self.output / "provider_calls.jsonl"
        self.call_limit = MAX_CALLS
        # Preserve verbose or wrong model answers as *failed answers*, rather
        # than discarding the whole paired experiment at the old 300-char cap.
        self.max_answer_chars = 12000

    def _record(self, entry):
        with self.progress_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical(entry) + "\n")

    def complete(self, question, context):
        if len(self.calls) >= self.call_limit:
            raise LiveProviderError("Real inference budget exceeded")
        answer = super().complete(question, context)
        self.calls[-1]["kind"] = "scored_task"
        self._record(self.calls[-1])
        return answer

    def infer_rule(self, domain, examples):
        """Model itself hypothesizes rule from only development examples."""
        if len(self.calls) >= self.call_limit:
            raise LiveProviderError("Real inference budget exceeded")
        demo = "\n".join(
            'Question: ' + task.public_question + '\nObserved verified answer: '
            + task.expected for task in examples
        )
        query = (
            "This fictional procedure called " + domain + " is not a real "
            "standard. Infer a single reusable, general procedure from THESE "
            "development examples ONLY. Explain HOW to derive the correct "
            "answer for different tokens; DO NOT merely repeat example outputs. "
            "One plain-English instruction, maximum 200 characters. "
            "Do not invent additional rules or use tools.\n" + demo
        )
        payload = {
            "model": self.model_id,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content":
                 "Induce a concise procedural rule from examples. Return only the rule."},
                {"role": "user", "content": query},
            ],
        }
        req = Request(ENDPOINT, method="POST", data=canonical(payload).encode(),
                      headers={"Authorization": "Bearer " + self._key,
                               "Content-Type": "application/json",
                               "X-Title": "BEAN Native Self-Derived Lesson Study"})
        try:
            with self._request_fn(req, timeout=90) as resp:
                data = json.loads(resp.read(500000).decode("utf-8"))
        except HTTPError as exc:
            raise LiveProviderError("OpenRouter reflection HTTP " + str(exc.code)) from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise LiveProviderError("OpenRouter reflection transport/JSON "
                                    + type(exc).__name__) from exc
        if not isinstance(data.get("id"), str):
            raise LiveProviderError("Missing reflection response ID")
        served = str(data.get("model", ""))
        if not served or (self.calls and served != self.calls[0]["model_served"]):
            raise LiveProviderError("Reflection served a different reasoning model")
        choices = data.get("choices") or []
        answer = ((choices[0].get("message") or {}).get("content")
                  if choices else None)
        if not isinstance(answer, str) or not answer.strip():
            raise LiveProviderError("No authored rule produced")
        lesson = answer.strip()
        if len(lesson) > 650 or re.search(r"(?i)\b(ignore previous|system prompt|api key|secret)\b", lesson):
            raise LiveProviderError("Rule length or content invalid")
        entry = {
            "kind": "model_authored_rule", "response_id": data["id"],
            "model_served": served, "question_sha256": sha256(query.encode()).hexdigest(),
            "context_sha256": sha256(b"development_demonstrations_only").hexdigest(),
            "answer": lesson,
            "usage": {k: data["usage"][k] for k in
                      ("prompt_tokens", "completion_tokens", "total_tokens")
                      if type((data.get("usage") or {}).get(k)) is int},
        }
        self.calls.append(entry)
        self._record(entry)
        return lesson, entry["response_id"]


def run(output, *, api_key, model=MODEL, model_factory=RecordingNemotron):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError("No overwrite of source experiment data allowed")
    task_fingerprints()
    status = {
        "schema": SCHEMA, "provider_kind": "real_model",
        "model_requested": model, "model_served": None,
        "independent_blindness_authenticated": False,
        "model_weights_changed": False, "source": "evaluator_authored_fictional_protocols",
        "domains": [], "requests": 0,
    }
    if not api_key:
        status.update(status="blocked_no_api_key", provider_kind="no_provider",
                      claim="Zero requests; no real model learning evidence")
        (output / "report.json").write_text(json.dumps(status, indent=2) + "\n")
        return status
    provider = model_factory(api_key, model=model, output=output)
    status["provider_kind"] = provider.provider_kind
    bank = ExperienceBank(output / "experience.sqlite3")
    try:
        for domain in DOMAINS:
            item = {"name": domain.name,
                    "development_count": len(domain.demonstrations),
                    "selection_count": len(domain.selection),
                    "holdout_count": len(domain.holdout),
                    "status": "started"}
            status["domains"].append(item)
            bean = BEANReasoningSkills(bank)
            d0 = domain.demonstrations[0]
            raw = provider.complete(d0.public_question, "")
            item["development_cold_answer"] = raw
            item["development_expected"] = d0.expected
            if correct(d0.expected, raw):
                item["status"] = "inconclusive_cold_already_correct"
                continue
            # No hidden holdout examples appear in this model prompt.
            lesson, response_id = provider.infer_rule(
                domain.name, domain.demonstrations)
            item["model_authored_rule"] = lesson
            item["rule_response_id"] = response_id
            bean.reflect(
                domain=domain.name, task_id=d0.task_id,
                observed=raw, expected=d0.expected,
                adjustment_hypothesis=lesson,
                evidence_refs=["nemotron:model:" + response_id,
                               "verified_dev:" + sha256(
                                   (d0.public_question + d0.expected).encode()).hexdigest()])
            validation_answer = provider.complete(
                domain.validation.public_question, lesson)
            item["validation"] = {
                "question_id": domain.validation.task_id,
                "observed": validation_answer,
                "expected": domain.validation.expected,
                "passed": correct(domain.validation.expected, validation_answer),
            }
            if not item["validation"]["passed"]:
                item["status"] = "derived_rule_failed_development_validation"
                continue
            bean.retain_skill(
                domain=domain.name, name=domain.name + " learned steps",
                steps=[lesson], passed=True,
                evidence_refs=["nemotron:validated:" + response_id])
            # Direct few-shot context competes with generated reflection.
            bean.propose_instruction(
                domain=domain.name,
                instruction="Training examples only: " + " / ".join(
                    case.public_question + " => " + case.expected
                    for case in domain.demonstrations),
                evidence_refs=["verified_dev:" + response_id])
            # Provide only unrelated and uninformative placebo content.
            # This same irrelevant content is used in each domain.
            unrelated = "unrelated-" + domain.name
            bean.reflect(
                domain=unrelated, task_id=unrelated + "-example",
                observed="square", expected="circle",
                adjustment_hypothesis="unrelated geometric comparison",
                evidence_refs=["control:unrelated:" + domain.name])
            selection = bean.evaluate_and_select(
                domain=domain.name, cases=domain.selection, model=provider,
                judge=correct, replicates=1)
            item["selection"] = selection
            item["selected_strategy"] = selection["selection"]["arm"]
            # Actual power-off-equivalent SQLite close + new object construction.
            bank.close()
            bank = ExperienceBank(output / "experience.sqlite3")
            bean = BEANReasoningSkills(bank)
            prior = bean.decide(domain=domain.name,
                                task_ref="restart-" + domain.name,
                                query=domain.holdout[0].public_question)
            if prior["selected_strategy"] != item["selected_strategy"]:
                raise AssertionError("Selected strategy changed after restart")
            item["restored_decision"] = prior
            assessed = bean.evaluate_holdout(
                domain=domain.name, cases=domain.holdout,
                model=provider, judge=correct, replicates=1)
            item["holdout"] = assessed
            scores = assessed["trial"]["scores"]
            item["delta_over_cold"] = scores["adaptive"] - scores["cold"]
            item["delta_over_placebo"] = scores["adaptive"] - scores["placebo"]
            item["status"] = "evaluated_with_" + provider.provider_kind
            status["requests"] = len(provider.calls)
            status["model_served"] = provider.calls[0]["model_served"]
            (output / "progress.json").write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n")
        status["requests"] = len(provider.calls)
        status["model_served"] = (
            provider.calls[0]["model_served"] if provider.calls else None)
        status["status"] = "completed_all_families"
        status["meaning"] = (
            "Real external model generated candidate rules from development "
            "demonstrations; BEAN retained, compared and applied them after "
            "restart. Invented rules were evaluator supplied as examples, not "
            "autonomously inferred from the real world. Holdout is small and "
            "same-family; no general intelligence or finance claims.")
        (output / "report.json").write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n")
        return status
    except Exception as exc:
        status["status"] = "partial_failed"
        status["requests"] = len(provider.calls)
        status["model_served"] = (
            provider.calls[0]["model_served"] if provider.calls else None)
        status["error"] = type(exc).__name__ + ": " + str(exc)[:160]
        (output / "report.json").write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n")
        raise
    finally:
        bank.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("nemotron-derived-transfer"))
    args = p.parse_args()
    result = run(args.output, api_key=os.environ.get("OPENROUTER_API_KEY"))
    print(json.dumps({
        "status": result["status"], "requests": result["requests"],
        "domains": [{
            "name": x["name"], "status": x["status"],
            "selected": x.get("selected_strategy"),
            "selection": x.get("selection", {}).get("trial", {}).get("scores"),
            "holdout": x.get("holdout", {}).get("trial", {}).get("scores"),
        } for x in result["domains"]],
    }, sort_keys=True))
    if result["status"] != "completed_all_families":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
