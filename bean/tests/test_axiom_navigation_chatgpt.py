"""Real Axiom navigation adapter contract using an instrumented local HTTP fake."""
from __future__ import annotations

import json
import unittest
from urllib.error import URLError

from integrations.chatgpt.axiom_navigation import (
    AxiomNavigationClient, NavigationUnavailable, validate_axiom_origin,
)


class FakeResponse:
    def __init__(self, item):
        self.payload = json.dumps(item).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.payload[:limit]


class LocalServerFixture:
    def __init__(self):
        self.saved = set()
        self.calls = []
        self.pages = [
            {"key": "quality", "label": "Quality Forge", "href": "/quality"},
            {"key": "bean", "label": "BEAN Intelligence", "href": "/intelligence"},
        ]

    def __call__(self, request, timeout):
        self.calls.append({
            "method": request.get_method(),
            "url": request.full_url,
            "timeout": timeout,
        })
        path = request.full_url.split("5060", 1)[-1]
        method = request.get_method()
        if path.startswith("/api/navigation?") and method == "GET":
            query = path.split("q=", 1)[-1].lower()
            return FakeResponse({"ok": True, "items": [
                item for item in self.pages if query in item["label"].lower()
                or query in item["key"].lower()
            ]})
        if path == "/api/favorites" and method == "GET":
            return FakeResponse({"ok": True, "items": [
                item for item in self.pages if item["key"] in self.saved
            ]})
        if path == "/api/favorites" and method == "POST":
            key = json.loads(request.data)["module_key"]
            if key not in {item["key"] for item in self.pages}:
                return FakeResponse({"ok": False, "error": "unknown"})
            created = key not in self.saved
            self.saved.add(key)
            return FakeResponse({"ok": True, "saved": True, "created": created,
                                 "favorite": next(p for p in self.pages if p["key"] == key)})
        if path.startswith("/api/favorites/") and method == "DELETE":
            key = path.rsplit("/", 1)[-1]
            existed = key in self.saved
            self.saved.discard(key)
            return FakeResponse({"ok": True, "removed": existed, "module_key": key})
        return FakeResponse({"ok": False})


class AxiomNavigationConnectorTests(unittest.TestCase):
    def test_local_url_only_no_proxy_or_remote_endpoint(self):
        self.assertEqual(validate_axiom_origin("http://127.0.0.1:5060/"),
                         "http://127.0.0.1:5060")
        for bad in ("http://example.com:5060", "https://localhost:5060",
                    "http://localhost:5060/x", "http://name:pass@localhost:5060",
                    "http://127.0.0.1", "file:///axiom.db", ""):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    validate_axiom_origin(bad)

    def test_actual_pin_then_menu_then_remove_through_api(self):
        fake = LocalServerFixture()
        client = AxiomNavigationClient(opener=fake)
        self.assertEqual(client.find("Quality")["items"][0]["href"], "/quality")
        before = client.list()
        self.assertEqual(before["items"], [])

        response = client.pin("quality")
        self.assertTrue(response["saved"])
        self.assertTrue(response["created"])
        self.assertEqual(response["favorite"]["key"], "quality")
        self.assertFalse(client.pin("quality")["created"])
        self.assertEqual([x["key"] for x in client.list()["items"]], ["quality"])
        self.assertTrue(client.remove("quality")["removed"])
        self.assertFalse(client.remove("quality")["removed"])
        self.assertEqual(client.list()["items"], [])
        self.assertTrue(all(
            call["url"].startswith("http://127.0.0.1:5060/")
            for call in fake.calls
        ))

    def test_do_not_claim_success_if_axiom_did_not_save(self):
        client = AxiomNavigationClient(opener=LocalServerFixture())
        with self.assertRaises(NavigationUnavailable):
            client.pin("does-not-exist")
        self.assertEqual(client.list()["items"], [])

    def test_reject_phantom_links_from_server(self):
        def bad(*_args):
            return FakeResponse({"ok": True, "items": [
                {"key": "spoof", "label": "spoof", "href": "//evil.example/"}
            ]})
        with self.assertRaises(NavigationUnavailable):
            AxiomNavigationClient(opener=bad).list()

    def test_clear_error_when_axiom_is_not_running(self):
        def offline(*_args):
            raise URLError("connection refused")
        with self.assertRaisesRegex(NavigationUnavailable, "start Axiom"):
            AxiomNavigationClient(opener=offline).list()


if __name__ == "__main__":
    unittest.main()
