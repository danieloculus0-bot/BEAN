"""Public AIscend demo: identity isolation, true source links, and controls.

The public HTML is intentionally read-only. These tests verify the wording and
static source, not a private exchange installation or external live data.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "docs" / "aiscend.html"
HOME = ROOT / "docs" / "index.html"


class DemoMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.actions = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "button" and a.get("data-scene"):
            self.actions.append(a["data-scene"])
        if tag == "img":
            self.images.append(a.get("src"))


class PublicAiscendDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = DEMO.read_text(encoding="utf-8")
        cls.home = HOME.read_text(encoding="utf-8")
        cls.markup = DemoMarkup()
        cls.markup.feed(cls.html)

    def test_home_and_demo_are_bidirectionally_linked(self):
        self.assertIn("./aiscend.html", self.home)
        self.assertIn("./index.html", self.markup.links)
        self.assertIn("./index.html#applications", self.markup.links)
        for item in ("demo", "how-it-works", "pet", "petMood", "demoTitle",
                     "researchTag", "journal", "gateText"):
            self.assertIn(item, self.markup.ids)

    def test_actual_official_mascot_and_retro_sprite(self):
        self.assertIn("./bean-official.webp", self.markup.images)
        self.assertTrue((DEMO.parent / "bean-official.webp").is_file())
        for marker in ("function drawPet(){", "48x48 Game Boy-inspired pixel canvas",
                       "oval(19,26,2.7,3.2,color.ink)",
                       "oval(30,26,2.7,3.2,color.ink)"):
            self.assertIn(marker, self.html)

    def test_demo_scenarios_are_interactive_but_never_connected(self):
        self.assertEqual(set(self.markup.actions),
                         {"watch", "experiment", "paper", "gate"})
        for marker in ("DEMO", "Read-only", "Sample", "NO WALLET CONNECTED",
                       "research-only", "not a private", "simulated"):
            self.assertIn(marker.casefold(), self.html.casefold())
        self.assertIn("document.querySelectorAll", self.html)
        self.assertNotIn("fetch('/api/", self.html)
        self.assertNotIn("fetch(\"/api/", self.html)
        self.assertNotIn("XMLHttpRequest", self.html)
        self.assertNotIn("walletSecret", self.html)
        self.assertNotIn("keyfile", self.html)

    def test_identity_and_account_identifiers_are_not_published(self):
        for pattern in (
            r"0x[0-9a-fA-F]{40}\b",
            r"\bsk-(?:or|proj)-[A-Za-z0-9_-]{12,}",
            r"\b[A-F0-9]{32,}\b",
            r"\b(?:seed phrase|private key is|api secret:)\s*\S+",
        ):
            self.assertIsNone(re.search(pattern, self.html, re.IGNORECASE), pattern)
        self.assertIn("Numeric tiles are illustrative", self.html)
        self.assertIn("No names, wallet addresses, account IDs", self.html)
        self.assertIn("not a private transaction log", self.html)

    @unittest.skipUnless(shutil.which("node"), "Node.js needed for browser script syntax check")
    def test_inline_browser_javascript_parses(self):
        scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", self.html)
        self.assertEqual(len(scripts), 1)
        out = subprocess.run([shutil.which("node"), "--check"],
                             input=scripts[0], text=True, capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == "__main__":
    unittest.main()
