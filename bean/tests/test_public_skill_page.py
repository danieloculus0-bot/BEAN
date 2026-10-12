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

    def test_differentiation_is_early_visible_and_evidence_citable(self):
        self.assertIn("difference", self.parser.anchors)
        self.assertIn("#difference", self.parser.links)
        self.assertLess(self.page.index('id="difference"'),
                        self.page.index('id="skills"'))
        for statement in (
            "The model thinks. BEAN keeps the receipts.",
            "A · Base LLM call",
            "B · Conventional tool agent",
            "C · BEAN's implementation",
            "Two real, tested source improvements",
            "14/14 development",
            "7/7 fresh holdout",
            "4 versus 6 held-out checks",
            "INCONCLUSIVE",
            "That controlled advantage has not yet been established.",
        ):
            with self.subTest(statement=statement):
                self.assertIn(statement, self.page)
        for reference in (
            "https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/15",
            "https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/17",
            "https://github.com/danieloculus0-bot/BEAN/pull/51",
            "https://github.com/danieloculus0-bot/BEAN/blob/main/docs/bean-causal-retention-lab023.md",
            "https://github.com/danieloculus0-bot/BEAN/actions/runs/38112389946",
        ):
            with self.subTest(reference=reference):
                self.assertIn(reference, self.parser.links)
        for path in ("docs/bean-causal-retention-lab023.md",
                     "docs/BEAN_LLM_REPAIR_EXPERIMENT_20261011.md"):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_lab026_research_claims_and_controls_are_clearly_scoped(self):
        self.assertIn("Four ways to test whether experience helps", self.page)
        for phrase in (
            "cold reasoning",
            "ordinary saved history",
            "evidence-ranked BEAN lessons",
            "unrelated placebo notes",
            "BEAN's learning advantage has not been demonstrated",
            "not the full BEAN architecture",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.page)
        for link in (
            "https://github.com/danieloculus0-bot/BEAN/pull/96",
            "https://github.com/danieloculus0-bot/BEAN/actions/runs/38181156634",
            "https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-causal-ablation-lab026-20261011/docs/bean-causal-ablation-lab026.md",
        ):
            with self.subTest(link=link):
                self.assertIn(link, self.parser.links)
        self.assertIn("INCONCLUSIVE", self.page)

    def test_universal_evidence_rank_is_present_and_accurately_scoped(self):
        self.assertIn("evidence-rank", self.parser.anchors)
        self.assertIn("#evidence-rank", self.parser.links)
        for statement in (
            "PageRank was for links. BEAN ranks evidence quality.",
            "scores the evidence", "before filing the hashed memory receipt",
            "not the probability that a claim is true",
            "insufficient", "attested", "contested",
            "doesn't automatically connect it to every application",
        ):
            with self.subTest(statement=statement):
                self.assertIn(statement, self.page)
        for path in (
            "bean/evaluation/evidence_rank.py",
            "bean/tests/test_evidence_rank.py",
            "docs/UNIVERSAL_EVIDENCE_RANK.md",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)
                self.assertIn(
                    "https://github.com/danieloculus0-bot/BEAN/blob/main/" + path,
                    self.parser.links,
                )
        self.assertIn(
            "https://github.com/danieloculus0-bot/BEAN/actions/runs/38187572884",
            self.parser.links,
        )

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
