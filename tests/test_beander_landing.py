"""Browser and content checks for the public BEANder concept page.

These tests cover real DOM behavior, not a backend or matchmaking network.
"""
from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "docs" / "beander" / "index.html"


class Capture(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.hrefs = []
        self.details = 0
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            if a["id"] in self.ids:
                raise AssertionError("duplicate id: " + a["id"])
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag == "details":
            self.details += 1
        if tag == "button":
            self.buttons.append(a)


class PageContract(unittest.TestCase):
    def test_markup_links_and_copy(self):
        source = PAGE.read_text(encoding="utf-8")
        parsed = Capture()
        parsed.feed(source)
        self.assertIn("<!doctype html>", source.lower())
        self.assertGreaterEqual(parsed.details, 3)
        self.assertTrue({"main", "story", "how", "preview", "investors",
                         "chat", "choices", "restart"} <= parsed.ids)
        for href in parsed.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], parsed.ids)
        self.assertTrue(any(b.get("data-answer") == "curious" for b in parsed.buttons))
        self.assertTrue(any(b.get("data-answer") == "pass" for b in parsed.buttons))
        self.assertIn('href="./ai-review.html"', source)
        self.assertIn("A fictional little meet-cute", source)
        self.assertIn("interactive preview right here in your browser", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("sessionStorage", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("64,000", source)

    def test_existing_ai_and_relatable_match_copy(self):
        source = PAGE.read_text(encoding="utf-8")
        for phrase in ("ChatGPT", "Gemini", "Claude",
                       "Keep talking to the AI you trust.",
                       "BEANder is the bridge",
                       "Your AI, the one you already use",
                       "Ashley", "Kyle", "Sunday brunch"):
            self.assertIn(phrase, source)
        self.assertNotIn("<b>Your companion</b>", source)
        self.assertNotIn("soldering", source)
        self.assertNotIn("tinkering", source)
        self.assertNotIn("one little thing", source.lower())

    def test_assets_are_relative_and_no_private_operational_data(self):
        source = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertNotIn("BEAN_RELAY_AGENTS_JSON", source)
        self.assertNotIn("localhost:", source)
        self.assertNotIn("http://127.0.0.1", source)
        self.assertNotIn("feature/beander-vc", source)
        self.assertNotIn("experiment/logic", source)
        self.assertIn("prefers-reduced-motion", source)
        self.assertIn("aria-live=", source)


class BrowserContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise unittest.SkipTest("Playwright not installed; browser tests require it") from exc
        cls.tool = sync_playwright().start()
        cls.browser = cls.tool.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.tool.stop()

    def make_page(self, width=1280, height=800, reduced_motion=False):
        context = self.browser.new_context(
            viewport={"width": width, "height": height},
            reduced_motion="reduce" if reduced_motion else "no-preference")
        page = context.new_page()
        # Google Fonts is optional. All product interactions are offline.
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
        page.goto(PAGE.as_uri())
        return context, page

    def test_interactive_chat_both_paths_and_restart(self):
        context, page = self.make_page()
        try:
            issues = []
            page.on("pageerror", lambda e: issues.append(str(e)))
            page.get_by_role("button", name="Wait, cute. Tell me more").click()
            self.assertTrue(page.get_by_text("Okay wait, tell me more.", exact=True).count())
            self.assertEqual(page.get_by_role("button", name="Yeah, ask him").count(), 1)
            page.get_by_role("button", name="Yeah, ask him").click()
            self.assertTrue(page.get_by_text("No pressure.", exact=False).count())
            page.get_by_role("button", name="Start the conversation again").click()
            page.get_by_role("button", name="Not my vibe").click()
            self.assertTrue(page.get_by_text("somebody who feels more like your type.", exact=False).count())
            self.assertEqual(issues, [])
        finally:
            context.close()

    def test_details_and_page_layout_mobile(self):
        for width in (375, 768, 1366):
            with self.subTest(width=width):
                context, page = self.make_page(width, 820)
                try:
                    page.get_by_text("Do I need another AI?").click()
                    self.assertTrue(page.get_by_text("The idea is to use the assistant you already know.", exact=False).is_visible())
                    outside = page.evaluate(
                        "() => document.documentElement.scrollWidth - window.innerWidth")
                    self.assertLessEqual(outside, 2, "horizontal overflow at " + str(width))
                    self.assertTrue(page.locator("h1").is_visible())
                    self.assertTrue(page.locator("#investors").count())
                finally:
                    context.close()

    def test_reduced_motion_and_keyboard_support(self):
        context, page = self.make_page(390, 844, reduced_motion=True)
        try:
            self.assertEqual(page.locator(".reveal-on-scroll.shown").count(),
                             page.locator(".reveal-on-scroll").count())
            page.get_by_text("Wait, the AIs actually talk?").focus()
            page.keyboard.press("Enter")
            self.assertTrue(page.get_by_text("That's the plan.", exact=False).is_visible())
            self.assertEqual(page.evaluate(
                "() => getComputedStyle(document.documentElement).scrollBehavior"), "auto")
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
