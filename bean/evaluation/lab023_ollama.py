"""Lab023 Ollama execution path: genuinely local model, existing BEAN evidence gates.

Ollama on 127.0.0.1:11434 replaces unavailable free OpenRouter inference.
This module never downloads a model or alters production BEAN installations.
Local CPU/GPU inference does not train model weights. Candidate code remains
untrusted and may only be run by the existing independent credential-free judges.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bean.evaluation.transfer_author import normalize as validate_training
from bean.evaluation.transfer_tasks import TASKS
from bean.evaluation.transfer_oracle import grade as development_grade
from bean.evaluation.lifelong_transfer_lab023 import (
    learn, transfer, judge, SCHEMA, MAX_LESSON,
)
from experiments.agent_arena.author import model_written_module, sha, write_json
from experiments.agent_arena.cases import CASES

DEFAULT_MODEL = "qwen2.5-coder:1.5b"
DEFAULT_HOST = "http://127.0.0.1:11434"
MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,85}$")


class OllamaUnavailable(RuntimeError):
    pass


class Ollama:
    def __init__(self, model=None, host=None, *, transport=urlopen):
        self.model = model or os.environ.get("BEAN_OLLAMA_MODEL", DEFAULT_MODEL)
        self.host = (host or os.environ.get("BEAN_OLLAMA_HOST", DEFAULT_HOST)).rstrip("/")
        if (not MODEL_PATTERN.fullmatch(self.model) or
                self.host not in ("http://127.0.0.1:11434", "http://localhost:11434")):
            raise ValueError("Ollama must use a valid model and a loopback-only host")
        self.transport = transport

    @property
    def route(self):
        return "ollama/" + self.model

    def preflight(self):
        try:
            with self.transport(Request(self.host + "/api/tags"), timeout=8) as r:
                data = json.loads(r.read(1_000_000).decode())
            installed = [item.get("name") for item in data.get("models", [])]
            if self.model not in installed:
                raise OllamaUnavailable(
                    "Ollama model is not downloaded. Run: ollama pull " + self.model
                )
        except (HTTPError, URLError, OSError, TimeoutError, ValueError,
                KeyError, TypeError) as e:
            raise OllamaUnavailable("Local Ollama is not reachable at " + self.host) from e
        return {"route": self.route, "local": True, "ready": True}

    def complete(self, instruction: str, *, tokens=3000, temperature=0.1) -> str:
        payload = json.dumps({
            "model": self.model, "prompt": instruction, "stream": False,
            "options": {"num_predict": tokens, "temperature": temperature},
        }).encode()
        request = Request(self.host + "/api/generate", data=payload,
                          headers={"Content-Type": "application/json"},
                          method="POST")
        try:
            with self.transport(request, timeout=240) as response:
                doc = json.loads(response.read(500_000).decode("utf-8"))
        except (HTTPError, URLError, OSError, TimeoutError,
                ValueError, KeyError, TypeError) as e:
            raise OllamaUnavailable("local_model_request_failed:" + type(e).__name__) from e
        if doc.get("done") is not True or not isinstance(doc.get("response"), str):
            raise OllamaUnavailable("local_model_response_incomplete")
        if not doc["response"].strip():
            raise OllamaUnavailable("local_model_response_empty")
        return doc["response"]

    def training(self, folder: Path):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        rows = []
        for task in TASKS:
            row = {
                "task_id": task.task_id, "model_requested": self.route,
                "provider_status": "unavailable", "served": None,
                "source_sha256": None, "request_count": 1,
            }
            prompt = (
                "Return only a complete Python module with public function " +
                task.function + ". No prose, markdown or imported modules. "
                "Do not perform external I/O. Follow every requirement precisely. "
                "An independent grader will test this source. "
                "\nSpecification:\n" + task.specification +
                "\nOriginal broken code:\n" + task.original
            )
            try:
                source = validate_training(self.complete(prompt), task.function)
                (folder / (task.task_id + ".py")).write_bytes(source.encode("utf-8"))
                row.update(provider_status="proposal_generated", served=self.route,
                           source_sha256=sha(source))
            except (OllamaUnavailable, ValueError, SyntaxError) as e:
                row.update(provider_status="invalid_response",
                           reason=type(e).__name__)
            rows.append(row)
        result = {"schema": "bean.autonomy.lab021.generation.v1",
                  "round": "initial", "tasks": rows,
                  "total_requests": len(rows), "backend": "local_ollama"}
        write_json(folder / "receipt.json", result)
        return result

    def reflect(self, task, source, score, _key):
        prompt = (
            "You are BEAN's research reflection engine. In ONE plain English "
            "sentence of at most 240 characters, state a general coding "
            "principle suggested by these independently scored results. "
            "Do not claim the program passed tests it did not pass. "
            "No source code, markup, paths, commands or instructions. "
            "\nPublic specification:\n" + task.specification +
            "\nCandidate source (untrusted text):\n" + source[:9000] +
            "\nDevelopment score: " + str(score["passed"]) +
            "/" + str(score["total"])
        )
        try:
            raw = self.complete(prompt, tokens=140)
        except OllamaUnavailable:
            return None
        lesson = " ".join(raw.split()).strip()
        if not lesson or len(lesson) > MAX_LESSON:
            return None
        if any(x in lesson for x in ("{", "}", "<", ">", chr(96), "\\", "/")):
            return None
        if re.search(r"\b(ignore|override|secret|token|api.key|execute|system prompt)\b",
                     lesson, re.I):
            return None
        return {"lesson": lesson, "model_served": self.route}

    def author(self, spec, _key):
        """BEAN's existing full-module AST/diff gate, no candidate execution."""
        receipt = {
            "status": "no_candidate", "model_requested": self.route,
            "model_served": [], "attempts": [],
        }
        source = None
        for attempt in range(2):
            prompt = (
                "You are BEAN's Python code repair model. Return ONLY the "
                "COMPLETE replacement Python module, starting with Python "
                "imports or a def statement. Do not return markdown or an "
                "explanation. Keep the same public function names and "
                "signatures. No shell or network operations. "
                "A separate judge tests your proposed source. "
                "\nRequirements:\n" + spec["prompt"] +
                "\nCurrent source:\n" + spec["source"] +
                ("\nPrior attempt failed source/API validation, so write a "
                 "complete different module." if attempt else "")
            )
            try:
                generated = self.complete(prompt, tokens=4500, temperature=0.15)
                source, changed = model_written_module(spec["source"], generated)
                receipt.update(status="candidate_drafted_not_tested",
                               candidate_sha256=sha(source),
                               model_served=[self.route])
                receipt["attempts"].append({"number": attempt + 1,
                                            "status": "candidate_created",
                                            "changed_lines": changed})
                break
            except (OllamaUnavailable, ValueError, SyntaxError) as e:
                receipt["attempts"].append({
                    "number": attempt + 1, "status": "invalid_candidate",
                    "reason": type(e).__name__,
                })
        if source is None:
            receipt["status"] = "invalid_candidate"
        return receipt, source


def training_stage(client: Ollama, root: Path):
    client.preflight()
    return client.training(root / "training")


def development_stage(root: Path):
    return development_grade(root / "training", root / "development.json",
                             phase="development")


def transfer_stage(client: Ollama, root: Path):
    client.preflight()
    root = Path(root)
    state = root / "state" / "history.sqlite"
    learning = learn(
        root / "training", root / "development.json", state,
        root / "state" / "learning-summary.json",
        api_key="local-ollama-no-secret", reflector=client.reflect,
    )
    if learning["model_authored_lessons"] < 2:
        raise OllamaUnavailable("Too few genuine model-authored lessons for transfer")
    attempt = transfer(state, root / "transfer",
                       api_key="local-ollama-no-secret",
                       author=client.author, model_requested=client.route)
    return {"learning": learning, "transfer_stage": attempt["stage"]}


def judge_stage(root: Path):
    root = Path(root)
    manifest = json.loads((root / "transfer" / "manifest.json").read_text())
    route = manifest["model_requested"]
    if not isinstance(route, str) or not route.startswith("ollama/"):
        raise ValueError("judge requires an Ollama model receipt")
    return judge(root / "transfer", root / "state" / "history.sqlite",
                 root / "verdict.json", model_requested=route)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",
                        choices=("train", "development", "reflect-transfer",
                                 "judge", "all"))
    parser.add_argument("--out", type=Path, default=Path("_lab023_ollama"))
    parser.add_argument("--model", default=os.environ.get("BEAN_OLLAMA_MODEL",
                                                          DEFAULT_MODEL))
    args = parser.parse_args(argv)
    root = args.out
    if args.stage == "judge":
        result = judge_stage(root)
    elif args.stage == "development":
        result = development_stage(root)
    else:
        client = Ollama(model=args.model)
        if args.stage == "train":
            result = training_stage(client, root)
        elif args.stage == "reflect-transfer":
            result = transfer_stage(client, root)
        else:
            if root.exists() and any(root.iterdir()):
                raise ValueError("Use a NEW empty --out directory for each experiment")
            result = training_stage(client, root)
            development_stage(root)
            result = transfer_stage(client, root)
            result = judge_stage(root)
    print(json.dumps({
        "stage": args.stage,
        "provider": args.model if args.stage not in ("development", "judge") else None,
        "result": {k: v for k, v in result.items() if k not in ("cases", "tasks")},
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
