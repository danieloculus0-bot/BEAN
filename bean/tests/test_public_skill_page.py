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
        self.mascot_images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.anchors.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if tag == "svg" and "mascot-svg" in attributes.get("class", ""):
            self.svgs += 1
        if tag == "img" and "mascot-art" in attributes.get("class", "").split():
            self.mascot_images.append(attributes)


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
        # The existing public site now uses the actual official webp mascot
        # instead of an older inline SVG. Verify one rendered mascot AND its
        # local artifact/alt text, rather than asking for an obsolete tag.
        self.assertEqual(self.parser.svgs + len(self.parser.mascot_images), 1)
        if self.parser.mascot_images:
            image = self.parser.mascot_images[0]
            self.assertEqual(image.get("src"), "./bean-official.webp")
            self.assertIn("BEAN", image.get("alt", ""))
            self.assertTrue((PAGE.parent / "bean-official.webp").is_file())
        self.assertIn("--green:#7ed957;", self.page)
        self.assertIn("Cute name. <br>Serious reasoning.", self.page)
        self.assertIn("#skills", self.parser.links)

    def test_neural_model_section_is_grounded_in_sources_and_scope(self):
        self.assertIn("neural", self.parser.anchors)
        self.assertIn("#neural", self.parser.links)
        for phrase in ("Yes, BEAN uses a neural network.",
                       "Not claimed: native BEAN-trained weights or backpropagation",
                       "Those records do not modify neural-network weights.",
                       "session-only"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.page)
        for path in ("bean/reasoning/ollama_provider.py",
                     "bean/tests/test_ollama_reasoning_provider.py",
                     "docs/bean-autonomous-code-growth-lab019.md",
                     "docs/bean-watcher-contract.md"):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)
                self.assertIn("https://github.com/danieloculus0-bot/BEAN/blob/main/" + path,
                              self.parser.links)

    def test_crypto_application_is_citable_and_scoped(self):
        self.assertIn("applications", self.parser.anchors)
        self.assertIn("#applications", self.parser.links)
        for phrase in ("BEAN is helping power a real crypto trader.",
                       "Research selection by itself does not activate a live trading strategy.",
                       "AIscend's trading engines execute orders.",
                       "An accepted order is not necessarily a verified fill"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.page)
        for path in ("src/live.py", "src/advanced_live.py", "src/bean.py",
                     "src/bean_strategy_lab.py", "src/bean_policy.py"):
            with self.subTest(path=path):
                self.assertIn("https://github.com/danieloculus0-bot/AIscend/blob/main/" + path,
                              self.parser.links)
        self.assertIn("https://github.com/danieloculus0-bot/AIscend/actions/runs/38174689361",
                      self.parser.links)

    def test_autonomous_engineering_and_fast_market_research_are_scoped(self):
        self.assertIn("autonomy", self.parser.anchors)
        self.assertIn("#autonomy", self.parser.links)
        for claim in (
            "BEAN writes real code. Independent tests decide what ships.",
            "Zero verified promotions",
            "Five-minute strategy research",
            "Independent forward paper trials",
            "Ollama-powered code engineer",
            "Metamorphic defect hunter",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, self.page)
        for url in (
            "https://github.com/danieloculus0-bot/BEAN/actions/runs/38175931431",
            "https://github.com/danieloculus0-bot/BEAN/blob/main/bean/evaluation/autonomous_selfrepair_verify.py",
            "https://github.com/danieloculus0-bot/AIscend/blob/main/src/bean_five_minute.py",
            "https://github.com/danieloculus0-bot/AIscend/blob/main/src/bean_research_supervisor.py",
            "https://github.com/danieloculus0-bot/AIscend/blob/main/docs/BEAN_UNATTENDED_LOCAL_ENGINEER.md",
            "https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/BEAN_METAMORPHIC_DISCOVERY_LAB.md",
        ):
            with self.subTest(url=url):
                self.assertIn(url, self.parser.links)

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
