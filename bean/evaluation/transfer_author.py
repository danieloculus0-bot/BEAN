"""Lab021: bounded external LLM code author, with no model-source execution.

Runs ONLY in credential-bearing generation jobs. Model replies become hashed
artifacts evaluated by independent no-secret CI. No paid fallback.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .transfer_tasks import TASKS

ROUTE = "openrouter/free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def normalize(source: str, required: str) -> str:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("empty_content")
    source = source.strip()
    if "```" in source:
        blocks = re.findall(r"```(?:python|py)?[ \t]*\r?\n(.*?)```", source, re.I | re.S)
        if len(blocks) != 1:
            raise ValueError("ambiguous_code_blocks")
        source = blocks[0].strip()
    if len(source) > 12000:
        raise ValueError("oversize_source")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError("invalid_python") from exc
    if not any(isinstance(node, ast.FunctionDef) and node.name == required
               for node in tree.body):
        raise ValueError("missing_required_function")
    return source + "\n"


def ask_model(task, api_key: str, *, feedback: dict | None = None, request_fn=urlopen):
    prompt = (
        "You are BEAN's experimental Python repair agent. Return ONLY a complete "
        "Python module defining exactly the requested public function. Do not "
        "import modules, read files, use network, or execute shell. A different "
        "machine grades on withheld randomized and edge-case tests. Keep code "
        "deterministic and handle all specified constraints.\n\n"
        "Objective ID: " + task.task_id + "\nSpecification: " + task.specification
        + "\nCurrent buggy code:\n" + task.original
    )
    if feedback:
        prompt += ("\nYour prior attempt was evaluated on private cases and did not "
                   "meet the bar. Passes: " + str(int(feedback.get("passed", 0)))
                   + "/" + str(int(feedback.get("total", 0)))
                   + ". Think through edge cases and produce a distinct, more "
                   "complete implementation. You will NOT receive individual "
                   "held-out inputs, expected answers, or traceback.")
    body = {"model": ROUTE, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2600, "temperature": 0.2, "stream": False}
    req = Request(ENDPOINT, data=json.dumps(body).encode("utf-8"),
                  headers={"Authorization": "Bearer " + api_key,
                           "Content-Type": "application/json",
                           "X-Title": "BEAN Lab021 Generalization"}, method="POST")
    with request_fn(req, timeout=75) as response:
        message = json.loads(response.read(400000).decode("utf-8"))
    if not isinstance(message, dict) or message.get("error"):
        raise ValueError("provider_error")
    choice = (message.get("choices") or [{}])[0]
    raw = (choice.get("message") or {}).get("content")
    if isinstance(raw, list):
        raw = "\n".join(x.get("text", "") for x in raw
                        if isinstance(x, dict) and x.get("type") == "text"
                        and isinstance(x.get("text"), str))
    code = normalize(raw, task.function)
    name = str(message.get("model", "unknown"))[:120]
    return code, name


def generate(output_dir: Path, *, api_key: str | None = None,
             feedback_file: Path | None = None, request_fn=urlopen) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    feedback = {}
    if feedback_file is not None:
        doc = json.loads(feedback_file.read_text(encoding="utf-8"))
        feedback = {x["task_id"]: x for x in doc["tasks"]}
    key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
    results = []
    for task in TASKS:
        prior = feedback.get(task.task_id)
        record = {"task_id": task.task_id, "model_requested": ROUTE,
                  "provider_status": "unavailable", "served": None,
                  "source_sha256": None, "request_count": 0}
        if prior and prior.get("passed") == prior.get("total") and prior.get("total", 0) > 0:
            record["provider_status"] = "already_passed"
        elif not key:
            record["reason"] = "secret_unavailable"
        else:
            record["request_count"] = 1
            try:
                source, model = ask_model(task, key, feedback=prior, request_fn=request_fn)
                (output_dir / (task.task_id + ".py")).write_bytes(source.encode("utf-8"))
                record.update(provider_status="proposal_generated", served=model,
                              source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest())
            except HTTPError as exc:
                record["reason"] = "http_" + str(exc.code)
            except (URLError, TimeoutError, OSError) as exc:
                record["reason"] = "transport_" + type(exc).__name__
            except (ValueError, KeyError, TypeError, IndexError, SyntaxError) as exc:
                permitted = {
                    "empty_content", "ambiguous_code_blocks", "oversize_source",
                    "invalid_python", "missing_required_function", "provider_error",
                }
                record["provider_status"] = "invalid_response"
                record["reason"] = str(exc) if str(exc) in permitted else "malformed_response"
        results.append(record)
    receipt = {"schema": "bean.autonomy.lab021.generation.v1",
               "round": "revision" if feedback_file is not None else "initial",
               "tasks": results, "total_requests": sum(x["request_count"] for x in results)}
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--feedback", type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.out, feedback_file=args.feedback), indent=2))


if __name__ == "__main__":
    main()
