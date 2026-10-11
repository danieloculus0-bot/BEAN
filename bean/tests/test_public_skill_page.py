"""Protect BEAN's public skills page from unsupported claims and broken local links.

This only verifies static markup/source references, not live GitHub Pages availability.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "index.html"


class SiteLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.svgs = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.anchors.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if tag == "svg" and "mascot-svg" in attributes.get("class", ""):
            self.svgs += 1


class PublicSkillsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.parser = SiteLinks()
        cls.parser.feed(cls.page)

    def test_mint_mascot_and_existing_anchors_survive(self):
        for anchor in ("top", "difference", "skills", "proof",
                       "quickstart", "research", "community"):
            self.assertIn(anchor, self.parser.anchors)
        self.assertEqual(self.parser.svgs, 1)
        self.assertIn("--green:#7ed957;", self.page)
        self.assertIn("Cute name. <br>Serious reasoning.", self.page)
        self.assertIn("#skills", self.parser.links)

    def test_new_skills_have_reproducible_refs(self):
        links = self.parser.links
        required = [
            "https://github.com/danieloculus0-bot/BEAN/blob/main/examples/restart_continuity.py",
            "https://github.com/danieloculus0-bot/BEAN/blob/main/bean/tests/test_restart_continuity_demo.py",
            "https://github.com/danieloculus0-bot/BEAN/blob/main/docs/BEAN_USEFULNESS_AUDIT_2026-10-11.md",
            "https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/DAILY_EXCEPTION_BRIEF.md",
            "https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/tests/test_daily_brief.py",
        ]
        for url in required:
            with self.subTest(url=url):
                self.assertIn(url, links)
        for file in ("examples/restart_continuity.py",
                     "bean/tests/test_restart_continuity_demo.py",
                     "docs/BEAN_USEFULNESS_AUDIT_2026-10-11.md"):
            self.assertTrue((ROOT / file).is_file(), file)

    def test_demo_claims_preserve_operational_boundaries(self):
        for text in ("python -m examples.restart_continuity",
                     "python -m ezbean.daily_brief",
                     "PYTHONPATH=src",
                     "mock provider", "not a live ERP",
                     "N/A", "pending proposal", "temporary SQLite"):
            with self.subTest(text=text):
                self.assertIn(text.casefold(), self.page.casefold())

    def test_internal_navigation_targets_exist(self):
        for href in self.parser.links:
            if href.startswith("#"):
                self.assertIn(href[1:], self.parser.anchors, href)


if __name__ == "__main__":
    unittest.main()
