"""Verify a deployed BEAN guest gateway, then optionally publish its URL locally."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ORIGIN = "https://danieloculus0-bot.github.io"


def verify(endpoint):
    u = urlsplit(endpoint)
    if (u.scheme != "https" or not u.hostname or u.username or u.password
            or u.path not in ("", "/") or u.query or u.fragment):
        raise ValueError("Expected a bare HTTPS gateway origin")
    endpoint = "https://" + u.netloc

    def request(route, data=None, method=None):
        headers = {"Origin": ORIGIN}
        if method == "OPTIONS":
            headers.update({"Access-Control-Request-Method": "POST",
                            "Access-Control-Request-Headers": "content-type"})
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(endpoint + route,
                      data=None if data is None else json.dumps(data).encode(),
                      headers=headers, method=method)
        with urlopen(req, timeout=210) as response:
            if response.geturl() != endpoint + route:
                raise RuntimeError("Unexpected redirect")
            if response.headers.get("Access-Control-Allow-Origin") != ORIGIN:
                raise RuntimeError("GitHub Pages CORS origin not allowed")
            if method == "OPTIONS":
                methods = response.headers.get("Access-Control-Allow-Methods", "")
                allowed = response.headers.get("Access-Control-Allow-Headers", "")
                if ("POST" not in methods or "content-type" not in allowed.lower()):
                    raise RuntimeError("Chat preflight does not allow JSON POST")
                return None
            return json.load(response)

    health = request("/api/health")
    if not (health.get("service") == "BEAN guest Core"
            and health.get("native_solver") is True
            and health.get("model_present") is True
            and health.get("memory") == "client_owned"
            and health.get("personal_history_retained") is False
            and health.get("production_memory_exposed") is False):
        raise RuntimeError("Gateway health contract failed")
    request("/api/chat", method="OPTIONS")
    orbit = request("/api/orbit", {"body": "earth", "altitude_km": 400})
    speed = float(orbit["result"]["circular_speed_km_s"])
    if not 7.67 < speed < 7.68:
        raise RuntimeError("Native orbit response did not match expected range")
    chat = request("/api/chat", {"message": "Compute 19 times 7. Respond with only the integer.", "context": []})
    if not (str(chat.get("answer", "")).strip() == "133"
            and chat.get("provider") == "local_llamacpp"
            and chat.get("model") == health.get("model")
            and chat.get("memory") == "client_owned"
            and chat.get("personal_history_retained") is False
            and len(chat.get("receipt_id", "")) == 64):
        raise RuntimeError("Real model response or receipt contract failed")
    return {"endpoint": endpoint}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("endpoint")
    p.add_argument("--write", type=Path, help="Write cloud-endpoint.json only after successful verification")
    args = p.parse_args()
    config = verify(args.endpoint)
    if args.write:
        args.write.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(config))


if __name__ == "__main__":
    main()
