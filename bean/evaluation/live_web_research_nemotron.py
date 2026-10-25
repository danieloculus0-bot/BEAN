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
        "provider_requests": 0,
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
    service = NativeReasoningService(
        out / "experience.sqlite3",
        model=OpenRouterProvider(model_name=MODEL, api_key=key))
    try:
        tool = WebResearchService(
            service, sources=PublicWebSources(brave_key=""))
        tool.sources.brave_key = None  # fix index for comparable no-key control
        try:
            answer = tool.investigate(
                domain="chemistry", task_ref="fixed-public-smoke",
                question=QUESTION, provider="wikipedia",
                max_pages=2)
        except Exception as exc:
            report.update(status="failed_public_web_or_model",
                          error_class=type(exc).__name__,
                          provider_requests=tool.sources.call_count)
        else:
            report.update({
                "status": answer["answer_status"],
                "provider_requests": tool.sources.call_count,
                "source_count": answer["source_count"],
                "source_urls": [x["url"] for x in answer["sources"]],
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
                      "provider_requests":answer["provider_requests"]},
                     sort_keys=True))
    if answer["status"] != "unverified_model_answer":
        raise SystemExit(2)
