#!/usr/bin/env python3
"""Check a locally installed llama.cpp server with BEAN's expected model alias."""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def probe(port: int = 8080, timeout_seconds: int = 150) -> dict:
    """Verify both readiness and a real response; fail with a useful reason."""
    if not 1024 <= port <= 65535:
        raise ValueError("Invalid local port")
    url = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout_seconds
    last_error = "No response"
    while time.monotonic() < deadline:
        try:
            with opener.open(url + "/health", timeout=3) as response:
                health = json.loads(response.read(4096))
                if response.status == 200 and health.get("status") == "ok":
                    break
                last_error = "Model still loading"
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = type(exc).__name__
        time.sleep(2)
    else:
        return {"ok": False, "stage": "health", "error": last_error}
    req = Request(
        url + "/v1/chat/completions",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "model": "bean-local",
            "messages": [{"role": "user", "content": "Reply with the single word READY."}],
            "max_tokens": 24,
            "stream": False,
        }).encode("utf-8"),
    )
    try:
        with opener.open(req, timeout=75) as response:
            data = json.loads(response.read(16384))
        reply = data["choices"][0]["message"]["content"]
        served = data["model"]
        if not isinstance(reply, str) or not reply.strip() or served != "bean-local":
            return {"ok": False, "stage": "inference", "error": "Empty response or unexpected model alias"}
        return {"ok": True, "stage": "inference", "model": served,
                "response_preview": reply.strip()[:150]}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        return {"ok": False, "stage": "inference", "error": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description="BEAN local llama.cpp inference smoke check")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    result = probe(args.port)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
