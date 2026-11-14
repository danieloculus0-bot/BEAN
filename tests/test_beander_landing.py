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
        self.assertIn("No accounts, matching service, or live dating network yet", source)
        self.assertIn("runs entirely in your browser", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("sessionStorage", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("64,000", source)

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
            page.get_by_role("button", name="I'm curious").click()
            self.assertTrue(page.get_by_text("Tell me more.", exact=False).count())
            self.assertEqual(page.get_by_role("button", name="Yes, please").count(), 1)
            page.get_by_role("button", name="Yes, please").click()
            self.assertTrue(page.get_by_text("whether the interest is mutual", exact=False).count())
            page.get_by_role("button", name="Start the conversation again").click()
            page.get_by_role("button", name="Not this time").click()
            self.assertTrue(page.get_by_text("We'll keep looking.", exact=False).count())
            self.assertEqual(issues, [])
        finally:
            context.close()

    def test_details_and_page_layout_mobile(self):
        for width in (375, 768, 1366):
            with self.subTest(width=width):
                context, page = self.make_page(width, 820)
                try:
                    page.get_by_text("Okay, but how does it learn?").click()
                    self.assertTrue(page.get_by_text("Through a guided introduction", exact=False).is_visible())
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
