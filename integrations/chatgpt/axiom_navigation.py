"""Local Axiom navigation adapter for BEAN's optional ChatGPT tool surface.

Only registered Axiom module keys can be pinned. This uses real Axiom HTTP
responses, never invents saved state. The local-only contract is not a
public multiuser authentication scheme.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import ProxyHandler, Request, build_opener


class NavigationUnavailable(RuntimeError):
    pass


def validate_axiom_origin(value: str) -> str:
    try:
        u = urlsplit(value)
        port = u.port
    except (ValueError, TypeError):
        raise ValueError("Invalid Axiom URL") from None
    if (u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost", "::1")
            or port is None or not 1 <= port <= 65535
            or u.username or u.password or u.path not in ("", "/")
            or u.query or u.fragment):
        raise ValueError("Axiom navigation connector must use an explicit localhost port")
    return value.rstrip("/")


class AxiomNavigationClient:
    """No network activity until a tool is actually called."""

    def __init__(self, origin: str | None = None, *, opener=None):
        self.origin = validate_axiom_origin(
            origin or os.environ.get("AXIOM_LOCAL_URL", "http://127.0.0.1:5060")
        )
        self._open = opener or build_opener(ProxyHandler({})).open

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(
            self.origin + path, data=data, method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with self._open(req, timeout=12) as res:
                response = res.read(65_537)
        except HTTPError as exc:
            raise NavigationUnavailable(
                "Axiom rejected navigation request (HTTP " + str(exc.code) + ")"
            ) from None
        except (URLError, OSError, TimeoutError) as exc:
            raise NavigationUnavailable(
                "Axiom local navigation unavailable; start Axiom on its configured port"
            ) from exc
        if len(response) > 65_536:
            raise NavigationUnavailable("Axiom navigation response too large")
        try:
            result = json.loads(response)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise NavigationUnavailable("Axiom returned invalid navigation JSON") from exc
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise NavigationUnavailable("Axiom did not confirm the navigation request")
        return result

    def find(self, query: str) -> dict:
        if not isinstance(query, str) or len(query) > 160:
            raise ValueError("Navigation query too long")
        result = self._call("GET", "/api/navigation?" + urlencode({"q": query}))
        return self._destinations(result)

    def list(self) -> dict:
        return self._destinations(self._call("GET", "/api/favorites"))

    @staticmethod
    def _destinations(data: dict) -> dict:
        items = data.get("items")
        if not isinstance(items, list):
            raise NavigationUnavailable("Axiom did not supply a destination list")
        clean = []
        for item in items:
            if (not isinstance(item, dict)
                    or not all(isinstance(item.get(k), str) for k in ("key", "label", "href"))
                    or not item["href"].startswith("/")
                    or item["href"].startswith("//")):
                raise NavigationUnavailable("Axiom supplied an invalid destination")
            clean.append({k: item[k] for k in ("key", "label", "href")})
        return {
            "ok": True, "items": clean, "scope": "local_axiom",
            "note": "Paths are relative to Axiom. Do not imply a publicly reachable URL.",
        }

    def pin(self, module_key: str) -> dict:
        if not isinstance(module_key, str) or len(module_key) > 64:
            raise ValueError("Valid Axiom module key required")
        result = self._call("POST", "/api/favorites", {"module_key": module_key})
        item = result.get("favorite")
        if result.get("saved") is not True or not isinstance(item, dict):
            raise NavigationUnavailable("Axiom did not confirm the favorite was saved")
        if item.get("key") != module_key:
            raise NavigationUnavailable("Axiom confirmed a different favorite")
        return {
            "ok": True, "saved": True, "created": result.get("created") is True,
            "favorite": {k: item[k] for k in ("key", "label", "href")},
            "scope": "local_axiom",
        }

    def remove(self, module_key: str) -> dict:
        if not isinstance(module_key, str) or len(module_key) > 64:
            raise ValueError("Valid Axiom module key required")
        result = self._call("DELETE", "/api/favorites/" + quote(module_key, safe=""))
        if result.get("module_key") != module_key or type(result.get("removed")) is not bool:
            raise NavigationUnavailable("Axiom returned an incomplete removal confirmation")
        return {
            "ok": True, "removed": result["removed"], "module_key": module_key,
            "scope": "local_axiom",
        }
