"""Single-call BEAN real free-model smoke without executing returned Python.

Called by credential-bearing GitHub Actions job. Produces source artifact and
a status receipt for a separate, credential-free evaluation job.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROUTE = "openrouter/free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
TASK = ("Fix the following Python function to clamp numeric scores to 0..100 "
        "inclusive, without changing its function name. Return ONLY the entire "
        "corrected Python module. An independent test suite is hidden from you.\n\n"
        "def clip_score(score):\n    return max(0, min(score, 101))\n")


def normalise(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("empty response")
    source = raw.strip()
    fence = chr(96) * 3
    if source.startswith(fence):
        lines = source.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith(fence):
            raise ValueError("unclosed code fence")
        source = "\n".join(lines[1:-1]).strip()
    if len(source) > 12000:
        raise ValueError("response too large")
    parsed = ast.parse(source, filename="proposal.py")
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "clip_score"
               for n in parsed.body):
        raise ValueError("expected clip_score function missing")
    return source + "\n"


def make_request(key: str, *, request_fn=urlopen) -> tuple[str, dict]:
    body = {"model": ROUTE, "messages": [{"role": "user", "content": TASK}],
            "temperature": 0.1, "max_tokens": 700, "stream": False}
    request = Request(ENDPOINT, data=json.dumps(body).encode("utf-8"),
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json",
                               "X-Title": "BEAN Free Model Experiment"}, method="POST")
    with request_fn(request, timeout=90) as response:
        reply = json.loads(response.read(400000).decode("utf-8"))
    model_used = str(reply.get("model", "unknown"))[:160]
    choice = (reply.get("choices") or [{}])[0]
    response_text = (choice.get("message") or {}).get("content")
    source = normalise(response_text)
    usage = {k: v for k, v in (reply.get("usage") or {}).items()
             if k in ("prompt_tokens", "completion_tokens", "total_tokens")
             and isinstance(v, (int, float)) and not isinstance(v, bool)}
    return source, {"model_served": model_used, "usage": usage}


def execute(output_dir: Path, *, api_key: str | None = None, request_fn=urlopen) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "bean.openrouter.free.live.v1", "model_requested": ROUTE,
               "attempted_requests": 0, "provider_status": "provider_unavailable",
               "generated_source_sha256": None, "model_served": None, "usage": {}}
    key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
    if not key:
        receipt["reason"] = "OPENROUTER_API_KEY not present in workflow environment"
    else:
        receipt["attempted_requests"] = 1
        try:
            source, metadata = make_request(key, request_fn=request_fn)
            (output_dir / "proposal.py").write_text(source, encoding="utf-8")
            receipt.update({"provider_status": "proposal_generated",
                            "generated_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                            "model_served": metadata["model_served"], "usage": metadata["usage"]})
        except HTTPError as exc:
            receipt["reason"] = "OpenRouter HTTP " + str(exc.code)
        except (URLError, TimeoutError, OSError) as exc:
            receipt["reason"] = "transport unavailable: " + type(exc).__name__
        except (ValueError, KeyError, TypeError, IndexError, SyntaxError) as exc:
            receipt["provider_status"] = "invalid_response"
            receipt["reason"] = "invalid model response: " + type(exc).__name__
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("live-probe-output"))
    args = parser.parse_args()
    receipt = execute(args.out)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a", encoding="utf-8") as f:
        f.write("provider_status=" + receipt["provider_status"] + "\n")


if __name__ == "__main__":
    main()
