"""Static regression checks for BEAN's plain-language public homepage.

The detailed research lab and demos have dedicated pages. This suite checks
current claims and links without restoring deleted technical-homepage markup.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import unittest
import re

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "index.html"


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get("id"):
            self.ids.add(data["id"])
        if tag == "a":
            self.links.append(data)
        if tag == "img":
            self.images.append(data)


class PublicSkillsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.dom = Markup()
        cls.dom.feed(cls.html)
        cls.hrefs = [x["href"] for x in cls.dom.links if x.get("href")]

    def test_document_integrity(self):
        self.assertEqual(self.html.count("<!doctype html>"), 1)
        self.assertEqual(self.html.count("</body>"), 1)
        self.assertEqual(self.html.count("</html>"), 1)
        self.assertRegex(self.html, r"</body>\s*</html>\s*\Z")

    def test_plain_language_and_claim_boundaries(self):
        for phrase in ("What if AI could", "learn from yesterday?",
                       "memory, evidence and feedback", "Still in development",
                       "No claims of finished AGI or consciousness",
                       "aren't yet one seamless general-purpose intelligence"):
            self.assertIn(phrase.casefold(), self.html.casefold())
        self.assertNotIn("BEAN has achieved AGI", self.html)

    def test_mascot_accessibility_and_brand(self):
        imgs = [x for x in self.dom.images if
                x.get("src") == "./bean-official.webp"]
        self.assertEqual(len(imgs), 2)
        self.assertTrue(any(x.get("alt") == "BEAN project mascot" for x in imgs))
        self.assertTrue((PAGE.parent / "bean-official.webp").is_file())
        self.assertIn("prefers-reduced-motion:reduce", self.html)
        self.assertIn("a:focus-visible", self.html)
        self.assertIn('aria-label="Main navigation"', self.html)
        self.assertIn('class="skip" href="#main"', self.html)

    def test_sections_and_internal_anchors(self):
        for section in ("main", "what", "capabilities", "how", "real",
                        "learning", "lab", "questions", "start"):
            self.assertIn(section, self.dom.ids)
        for href in self.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], self.dom.ids, href)

    def test_local_links_resolve_to_real_files(self):
        for href in self.hrefs:
            url = urlsplit(href)
            if url.scheme or url.netloc or not url.path:
                continue
            with self.subTest(href=href):
                self.assertFalse(url.path.startswith("/"))
                target = (PAGE.parent / url.path).resolve()
                self.assertTrue(target.is_relative_to(PAGE.parent.resolve()))
                if target.is_dir():
                    target = target / "index.html"
                self.assertTrue(target.is_file(), str(target))

    def test_learning_numbers_are_scoped_and_source_linked(self):
        for phrase in ("12.04", "1.36", "200-game held-out test",
                       "not an overall intelligence score",
                       "not proof it could automatically master"):
            self.assertIn(phrase.casefold(), self.html.casefold())
        self.assertTrue(any("sponge_breakout/evidence/score_ledger.jsonl"
                            in href for href in self.hrefs))
        self.assertIn("./research-lab.html", self.hrefs)
        self.assertIn("./portfolio/bean-learning/", self.hrefs)

    def test_research_and_demo_routes_are_preserved(self):
        for link in ("./for-ai-developers.html", "./portfolio/",
                     "./aiscend.html", "./axiom.html", "./rubiks-cube.html",
                     "https://github.com/danieloculus0-bot/BEAN"):
            self.assertIn(link, self.hrefs)
        self.assertIn('id="aiscend"', self.html)
        self.assertIn("does not promise profitable trades", self.html)

    def test_external_new_tab_links_are_safe(self):
        for link in self.dom.links:
            if link.get("target", "").lower() == "_blank":
                self.assertIn("noopener", link.get("rel", "").split())
                self.assertIn("noreferrer", link.get("rel", "").split())

    def test_no_public_browser_memory_or_fake_wallet(self):
        for retired in ("try-bean.html", "try-bean-memory.js",
                        'id="paperBuy"', "PAPER TRADING LAB"):
            self.assertNotIn(retired, self.html)
        self.assertNotRegex(self.html, r"\bsk-(?:or|proj)-[A-Za-z0-9_-]{12,}")
        self.assertNotRegex(self.html, r"\b0x[0-9a-fA-F]{40}\b")

    def test_public_metadata(self):
        for marker in ('name="description"', 'property="og:title"',
                       'property="og:image"', 'rel="canonical"'):
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
