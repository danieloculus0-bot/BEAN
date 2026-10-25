"""Regression checks for the current BEAN public laboratory landing page.

Tests verify the current dark-theme design and source-grounded evidence. The
pre-redesign checks referred to deleted anchors and an older HTML template.
These are static source checks, not claims of live site deployment.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "index.html"


class SiteMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.images = []
        self.lab_cards = []
        self._lab = False

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if props.get("id"):
            self.ids.add(props["id"])
            if props["id"] == "experiments":
                self._lab = True
        if tag == "a" and "href" in props:
            self.links.append(props["href"])
        if tag == "img":
            self.images.append(props)
        if tag == "article" and "card" in props.get("class", "").split():
            self.lab_cards.append(props)

    def handle_endtag(self, tag):
        pass


class PublicSkillsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.markup = SiteMarkup()
        cls.markup.feed(cls.page)

    def test_project_brand_mark_and_research_hero(self):
        marks = [x for x in self.markup.images
                 if x.get("src") == "./bean-official.webp"]
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0]["alt"], "BEAN brand mark")
        self.assertTrue((PAGE.parent / "bean-official.webp").is_file())
        self.assertIn('class="hero-research"', self.page)
        self.assertIn("View the experiment and evidence", self.page)
        self.assertIn("object-fit:contain", self.page)
        self.assertIn("flex-shrink:0", self.page)
        self.assertIn(".brand img{display:block;width:54px;height:62px", self.page)
        self.assertIn("height:auto;object-fit:contain", self.page)

    def test_identity_theme_and_home_links(self):
        for phrase in ("Memory. Evidence.", "Judgment.",
                       "Published results link to code and test evidence.",
                       "--accent:#79DE4B", "237 / 240"):
            self.assertIn(phrase, self.page)
        for href in ("#lab", "#learning", "#capabilities", "#aiscend", "#start",
                     "./aiscend.html", "./portfolio/bean-learning/",
                     "https://github.com/danieloculus0-bot/BEAN"):
            self.assertIn(href, self.markup.links)
        self.assertIn('href="./aiscend.html" target="_blank" rel="noopener noreferrer"',
                      self.page)
        self.assertIn("Explore the public AIscend demo", self.page)

    def test_removed_browser_memory_playground_stays_unpublished(self):
        # Public calls to action must not misrepresent localStorage as BEAN Core.
        retired = ("try-bean.html", "try-bean-memory.js")
        for name in retired:
            self.assertFalse((PAGE.parent / name).exists(), name)
            self.assertNotIn(name, self.page)
        self.assertNotIn('id="try-bean"', self.page)
        self.assertNotIn("Try BEAN without login", self.page)
        self.assertNotIn("browser-local playground", self.page)
        self.assertIn('href="#start"', self.page)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("try-bean.html", readme)
        self.assertIn("## Verify BEAN Core locally", readme)

    def test_learning_claims_are_reproducible_and_scoped(self):
        # Both original and independently reseeded experiment must be
        # represented, with comparable cold controls and an immutable receipt.
        for phrase in ("11.305", "1.355", "12.040", "1.360", "98.5%",
                       "200-game holdout", "disjoint validation and holdout seeds",
                       "different training games", "Windows and Linux",
                       "not evidence of improved learning algorithms",
                       "SHA-256", "scored"):
            self.assertIn(phrase.casefold(), self.page.casefold())
        for href in (
            "https://github.com/danieloculus0-bot/BEAN/pull/99",
            "https://github.com/danieloculus0-bot/BEAN/actions/runs/39536702492",
            "https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-sponge-core-20261011/experiments/sponge_breakout/evidence/score_ledger.jsonl",
        ):
            self.assertIn(href, self.markup.links)
        self.assertNotIn("no independent training-seed replication yet", self.page.casefold())

    def test_neuroevolution_has_negative_findings_and_sources(self):
        for phrase in ("44", "45", "46", "9.683", "4.833",
                       "not a replicated evolutionary advantage",
                       "two validation cohorts", "standard DQN"):
            self.assertIn(phrase.casefold(), self.page.casefold())
        for href in ("https://github.com/danieloculus0-bot/BEAN/pull/107",
                     "https://github.com/danieloculus0-bot/BEAN/actions/runs/38229337741"):
            self.assertIn(href, self.markup.links)
        self.assertIn("not DeepMind pixel Atari", self.page)
        self.assertIn("This is not a replicated evolutionary advantage", self.page.replace(
            "<strong>not a replicated evolutionary advantage</strong>",
            "This is not a replicated evolutionary advantage"))

    def test_readme_milestones_are_scoped_and_linked(self):
        for name in ("BEAN Watcher", "Local Windows voice",
                     "Read-only MCP preview", "GitHub evidence bridge"):
            self.assertIn(name, self.page)
        for suffix in (
            "/README.md",
            "/docs/bean-watcher-contract.md",
            "/docs/bean-local-voice.md",
            "/integrations/chatgpt/README.md",
            "/docs/bean-github-engineering-bridge.md",
        ):
            self.assertTrue(any(link.endswith(suffix) for link in self.markup.links),
                            suffix)
        self.assertIn("research-only", self.page)
        self.assertIn("now on Core main through PR #153", self.page)
        self.assertIn("id=\"judgment\"", self.page)
        self.assertIn("Adequate", self.page)
        self.assertIn("four-platform Core regression passed", self.page)
        self.assertIn("38257867402", self.page)

    def test_aiscend_preview_only_uses_real_fields(self):
        for value in ("Net liquidation", "Cash / USDC", "Wealth multiple",
                      "P/L", "GAME SCORE", "0 points", "2X",
                      "$25.60", "$6.20", "+$0.60", "1.0240"):
            self.assertIn(value, self.page)
        self.assertIn("sample account", self.page)
        self.assertIn("fabricated $100 buy/sell terminal was removed", self.page)
        self.assertNotIn("mock-bars", self.page)
        self.assertNotIn("Synthetic asset", self.page)
        self.assertNotIn("PAPER TRADING LAB", self.page)
        self.assertNotIn('id="paperBuy"', self.page)
        self.assertIn("https://github.com/danieloculus0-bot/AIscend/blob/main/templates/index.html",
                      self.markup.links)

    def test_specialist_battle_does_not_invent_wins(self):
        for phrase in ("OpenCode", "Goose", "OpenHands", "Continue", "Cline",
                       "five competitive verdicts", "INCONCLUSIVE",
                       "agent battle did", "newer Sponge or DQN evolution policy"):
            self.assertIn(phrase.casefold(), self.page.casefold())
        self.assertIn("https://github.com/danieloculus0-bot/BEAN/actions/runs/38187443602",
                      self.markup.links)

    def test_navigation_and_interactive_lab_filter_counts(self):
        for href in self.markup.links:
            if href.startswith("#"):
                self.assertIn(href[1:], self.markup.ids, href)
        self.assertEqual(len(self.markup.lab_cards), 8)
        self.assertIn("8 studies shown", self.page)
        self.assertIn("data-filter", self.page)
        self.assertIn("button.addEventListener('click'", self.page)
        self.assertIn("copy.addEventListener('click'", self.page)

    def test_no_duplicate_html_or_unsafe_browser_link(self):
        self.assertEqual(self.page.count("</html>"), 1)
        self.assertEqual(self.page.count("</body>"), 1)
        self.assertRegex(self.page, r"</body>\s*</html>\s*\Z")
        self.assertFalse(self.page.split("</html>", 1)[1].strip())
        self.assertIn("rel=\"noopener noreferrer\"", self.page)
        self.assertNotIn("0x" + "1" * 40, self.page)
        self.assertNotRegex(self.page, r"sk-(?:or|proj)-[A-Za-z0-9_-]{12,}")

    @unittest.skipUnless(shutil.which("node"), "Node.js needed for script syntax test")
    def test_home_inline_javascript_parses(self):
        scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", self.page)
        self.assertEqual(len(scripts), 1)
        for script in scripts:
            out = subprocess.run([shutil.which("node"), "--check"],
                                 input=script, text=True, capture_output=True)
            self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == "__main__":
    unittest.main()
