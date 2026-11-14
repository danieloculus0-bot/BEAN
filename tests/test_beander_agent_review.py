"""Public BEANder machine-readable evidence and visitor audit behavior."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "docs" / "beander"
MAIN_SHA = "a" * 40
RESEARCH_SHA = "b" * 40


class EvidenceContract(unittest.TestCase):
    def test_manifest_links_and_scope(self):
        manifest = json.loads((SITE / "agent-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "beander.ai_review.v1")
        self.assertEqual(len(manifest["code_evidence"]), 2)
        self.assertIn("experiment/logic/duovely-relay-20261113",
                      manifest["code_evidence"][1]["ref"])
        self.assertIn("exact", manifest["agent_request"].lower())
        self.assertNotIn("force", manifest["agent_request"].lower())
        self.assertNotIn("give a positive review", manifest["agent_request"].lower())
        self.assertIn("fictional", manifest["demo_type"])
        html = (SITE / "ai-review.html").read_text(encoding="utf-8")
        self.assertIn('href="./agent-manifest.json"', html)
        self.assertIn("api.github.com", html)
        self.assertIn('id="check"', html)
        self.assertIn('id="ai-prompt"', html)
        self.assertIn("private", html.lower())
        self.assertNotIn("OPENAI_API_KEY", html)
        self.assertNotIn("BEAN_RELAY_AGENTS_JSON", html)
        self.assertNotIn("localStorage", html)
        self.assertNotIn("sessionStorage", html)


class BrowserContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise unittest.SkipTest("Playwright required for interactive browser tests") from exc
        cls.engine = sync_playwright().start()
        cls.browser = cls.engine.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.engine.stop()

    def open(self, width=1280, break_api=False):
        ctx = self.browser.new_context(viewport={"width": width, "height": 810},
                                       reduced_motion="reduce")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())

        def serve(route):
            url = route.request.url
            if break_api:
                route.fulfill(status=403, headers={"Access-Control-Allow-Origin": "*"},
                              body='{"message":"rate limited"}', content_type="application/json")
                return
            if "/branches/main" in url:
                data = {"commit": {"sha": MAIN_SHA}}
            elif "/branches/experiment" in url:
                data = {"commit": {"sha": RESEARCH_SHA}}
            elif "/contents/docs/beander/index.html" in url:
                data = {"path": "docs/beander/index.html", "sha": "blob"}
            elif "beander-landing-test.yml" in url:
                data = {"workflow_runs": [{"event": "push", "head_sha": MAIN_SHA,
                                            "conclusion": "success", "id": 42}]}
            elif "bean-agent-relay-experiment.yml" in url:
                data = {"workflow_runs": [{"event": "push", "head_sha": RESEARCH_SHA,
                                            "conclusion": "success", "id": 57}]}
            else:
                data = {"message": "unexpected URL"}
            route.fulfill(status=200, content_type="application/json",
                          headers={"Access-Control-Allow-Origin": "*"},
                          body=json.dumps(data))

        page.route("https://api.github.com/**", serve)
        page.goto((SITE / "ai-review.html").as_uri())
        return ctx, page, errors

    def test_exact_commit_audit_passes_with_matching_public_evidence(self):
        ctx, page, errors = self.open()
        try:
            page.get_by_role("button", name="Run code evidence check").click()
            page.get_by_text("Source and both independent test suites verified.", exact=False).wait_for()
            receipt = json.loads(page.locator("#receipt").inner_text())
            self.assertEqual(receipt["main_sha"], MAIN_SHA)
            self.assertEqual(receipt["research_sha"], RESEARCH_SHA)
            for name in ("site", "browser", "relay"):
                self.assertIn(receipt["checks"][name]["status"], ("verified", "passed"))
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_api_failure_is_not_painted_as_success(self):
        ctx, page, errors = self.open(break_api=True)
        try:
            page.get_by_role("button", name="Run code evidence check").click()
            page.get_by_text("Evidence check completed.", exact=False).wait_for()
            receipt = json.loads(page.locator("#receipt").inner_text())
            for name in ("site", "browser", "relay"):
                self.assertNotIn(receipt["checks"][name]["status"], ("verified", "passed"))
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_accessible_mobile_visitor_review(self):
        for width in (375, 768, 1366):
            with self.subTest(width=width):
                ctx, page, errors = self.open(width=width)
                try:
                    self.assertTrue(page.get_by_role("heading", name="Let your AI fall in love with the idea.").count())
                    self.assertTrue(page.locator("#ai-prompt").get_attribute("readonly") is not None)
                    overflow = page.evaluate("() => document.documentElement.scrollWidth-window.innerWidth")
                    self.assertLessEqual(overflow, 2, "horizontal scroll at "+str(width))
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
