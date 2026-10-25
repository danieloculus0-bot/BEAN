"""Single bounded REAL model+web search smoke for BEAN's native research outlet.

No mock-model substitution, no repeated retries or inferred performance result.
It exercises public Wikipedia read → source journal → one actual Nemotron
answer. A positive answer is NOT source verification or learned intelligence.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import os

from bean.learning import NativeReasoningService
from bean.reasoning.openrouter_provider import OpenRouterProvider
from bean.research import WebResearchService, PublicWebSources


QUESTION = "What is the chemical symbol of tungsten?"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


def execute(output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "report.json"
    key = os.environ.get("OPENROUTER_API_KEY")
    report = {
        "schema": "bean.live_web_research_nemotron.v1",
        "real_model_requested": MODEL,
        "web_http_requests": 0,
        "model_attempts": 0,
        "search_mode": "wikipedia",
        "status": "started",
        "genuine_learning_proven": False,
        "fact_verified_by_bridge": False,
        "provider_result_hypothetical": False,
    }
    if not key:
        report["status"] = "blocked_no_openrouter_key"
        path.write_text(json.dumps(report, indent=2) + "\n")
        return report
    provider = OpenRouterProvider(model_name=MODEL, api_key=key)
    service = NativeReasoningService(out / "experience.sqlite3", model=provider)
    try:
        tool = WebResearchService(
            service, sources=PublicWebSources(brave_key=""))
        tool.sources.brave_key = None  # fix index for comparable no-key control
        report["model_attempts"] = 1
        try:
            answer = tool.investigate(
                domain="chemistry", task_ref="fixed-public-smoke",
                question=QUESTION, search_query="Tungsten",
                provider="wikipedia", max_pages=2)
        except Exception as exc:
            report.update(status="failed_public_web_or_model",
                          error_class=type(exc).__name__,
                          web_http_requests=tool.sources.call_count,
                          provider_failure_kind=provider.last_failure_kind or "unknown")
        else:
            report.update({
                "status": answer["answer_status"],
                "web_http_requests": tool.sources.call_count,
                "source_count": answer["source_count"],
                "source_urls": [x["url"] for x in answer["sources"]],
                "source_title_match": any(
                    x["url"] == "https://en.wikipedia.org/wiki/Tungsten"
                    for x in answer["sources"]),
                "provider_failure_kind": answer.get("provider_failure_kind")
                    or provider.last_failure_kind,
                "real_model_id": answer.get("model_id"),
                "answer": answer.get("answer"),
                "inference_receipt": answer.get("inference_receipt"),
                "journal_counts": service.status(),
            })
    finally:
        service.close()
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    answer = execute(args.output)
    print(json.dumps({"status":answer["status"],
                      "source_count":answer.get("source_count", 0),
                      "web_http_requests":answer["web_http_requests"],
                      "model_attempts":answer["model_attempts"],
                      "provider_failure_kind":answer.get("provider_failure_kind")},
                     sort_keys=True))
    if answer["status"] != "unverified_model_answer":
        raise SystemExit(2)
