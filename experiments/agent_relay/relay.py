"""Authenticated loopback HTTP transport for typed, ephemeral agent messages.

Credentials are supplied only at process startup; no storage or logging of
tokens, human profiles, message bodies, or request metadata. This is not E2EE.
"""
from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from threading import RLock
from urllib.parse import urlparse

from .protocol import IDENT, MAX_BYTES, validate_message


class Relay:
    def __init__(self, credentials: dict[str, str], queue_limit: int = 200):
        if not isinstance(credentials, dict) or len(credentials) < 2:
            raise ValueError("at least two agent credentials required")
        if not isinstance(queue_limit, int) or not 1 <= queue_limit <= 2000:
            raise ValueError("invalid queue bound")
        if any(not isinstance(k, str) or not IDENT.fullmatch(k)
               or not isinstance(v, str) or len(v) < 24 for k, v in credentials.items()):
            raise ValueError("invalid credentials")
        if len(set(credentials.values())) != len(credentials):
            raise ValueError("every agent must have a distinct capability")
        self._digests = {k: sha256(v.encode()).digest() for k, v in credentials.items()}
        self._inboxes = defaultdict(deque)
        self._seen = {}
        self._limit = queue_limit
        self._lock = RLock()

    def authenticate(self, bearer: str | None) -> str:
        if not isinstance(bearer, str) or not bearer.startswith("Bearer "):
            raise PermissionError("unauthorized")
        supplied = sha256(bearer[7:].encode()).digest()
        # Compare every digest, rather than early exit based on identity.
        found = [name for name, digest in self._digests.items()
                 if hmac.compare_digest(digest, supplied)]
        if len(found) != 1:
            raise PermissionError("unauthorized")
        return found[0]

    def deliver(self, agent: str, payload: dict) -> dict:
        item = validate_message(payload)
        if item["sender"] != agent:
            raise PermissionError("sender does not own capability")
        if item["recipient"] not in self._digests:
            raise ValueError("unknown recipient")
        key = (agent, item["message_id"])
        with self._lock:
            if key in self._seen:
                if self._seen[key] != item:
                    raise ValueError("conflicting replay for message_id")
                return {"accepted": False, "duplicate": True}
            inbox = self._inboxes[item["recipient"]]
            if len(inbox) >= self._limit:
                raise ValueError("recipient inbox full")
            self._seen[key] = dict(item)
            inbox.append(item)
        return {"accepted": True, "duplicate": False}

    def receive(self, agent: str, limit: int = 20) -> list[dict]:
        if agent not in self._digests or type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("invalid inbox request")
        with self._lock:
            inbox = self._inboxes[agent]
            return [inbox.popleft() for _ in range(min(limit, len(inbox)))]


def make_server(relay: Relay, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    if host != "127.0.0.1":
        raise ValueError("research server only binds loopback; use a separately reviewed TLS gateway")

    class Handler(BaseHTTPRequestHandler):
        server_version = "BEANRelay/0.1"
        sys_version = ""

        def log_message(self, *_args):
            # Avoid accidentally logging authorization or session metadata.
            return

        def respond(self, status: int, data: object):
            raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def actor(self):
            return relay.authenticate(self.headers.get("Authorization"))

        def do_GET(self):
            try:
                actor = self.actor()
                if urlparse(self.path).path != "/v1/inbox" or "?" in self.path:
                    return self.respond(404, {"error": "not_found"})
                return self.respond(200, {"messages": relay.receive(actor)})
            except PermissionError:
                return self.respond(401, {"error": "unauthorized"})
            except ValueError:
                return self.respond(400, {"error": "invalid_request"})

        def do_POST(self):
            try:
                actor = self.actor()
                if self.path != "/v1/messages":
                    return self.respond(404, {"error": "not_found"})
                size = self.headers.get("Content-Length", "")
                if not size.isascii() or not size.isdecimal():
                    return self.respond(400, {"error": "invalid_request"})
                length = int(size)
                if not 0 < length <= MAX_BYTES:
                    return self.respond(413, {"error": "message_size"})
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                result = relay.deliver(actor, payload)
                return self.respond(202, result)
            except PermissionError:
                return self.respond(403, {"error": "forbidden"})
            except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
                return self.respond(400, {"error": "invalid_request"})

    return ThreadingHTTPServer((host, port), Handler)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BEAN experimental local-only agent relay")
    parser.add_argument("--port", type=int, default=8779)
    args = parser.parse_args()
    creds = json.loads(os.environ.get("BEAN_RELAY_AGENTS_JSON", "{}"))
    relay = Relay(creds)
    server = make_server(relay, port=args.port)
    print("BEAN anonymous relay listening on loopback", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
