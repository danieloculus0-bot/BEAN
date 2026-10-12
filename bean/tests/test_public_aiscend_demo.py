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

    def test_public_market_prices_and_direct_links_are_read_only(self):
        self.assertIn("id=\"markets\"", self.html)
        self.assertIn("id=\"marketFreshness\"", self.html)
        self.assertIn("Coinbase Exchange public last-trade quotes", self.html)
        self.assertIn("https://api.exchange.coinbase.com/products/", self.html)
        self.assertIn("fetch(endpoint,{signal:abort.signal,cache:\"no-store\"})",
                      self.html)
        self.assertIn("response.ok", self.html)
        self.assertIn("Math.abs(Date.now()-timestamp)>15*60*1000", self.html)
        self.assertIn("Open any Coinbase market link", self.html)
        for ticker, slug in (
            ("BTC", "bitcoin"), ("ETH", "ethereum"),
            ("SOL", "solana"), ("DOGE", "dogecoin"),
        ):
            self.assertIn('id="market' + ticker + '"', self.html)
            self.assertIn("https://www.coinbase.com/price/" + slug,
                          self.markup.links)
        self.assertIn("https://exchange.coinbase.com/markets",
                      self.markup.links)
        # Live market reads are distinct from demo balance/research numbers.
        self.assertIn("sample", self.html)
        self.assertNotIn("Authorization: Bearer", self.html)

    def test_main_site_opens_demo_in_new_tab(self):
        self.assertIn('href="./aiscend.html" target="_blank" '
                      'rel="noopener noreferrer"', self.home)
        self.assertIn("Explore the public AIscend demo", self.home)

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

    def test_invented_paper_order_terminal_is_absent(self):
        # An unapproved website-only $100 paper terminal was added to the
        # original demo. Keep this module out rather than rebrand it as real.
        for text in ("PAPER TRADING LAB", 'id="paperBuy"',
                     'id="paperSell"', 'id="paperAuto"',
                     'id="paperChart"', 'id="paperScenario"',
                     'id="paper-lab"', "Synthetic asset",
                     "Starting paper capital: $100",
                     "function trade(buy)"):
            with self.subTest(text=text):
                self.assertNotIn(text, self.html)
        self.assertNotIn(".paper-lab", self.html)

    def test_actual_aiscend_research_is_source_grounded(self):
        self.assertIn('id="research-updates"', self.html)
        for text in ("seven rule families", "Unattended research supervisor",
                     "forward-only five-minute candles",
                     "not extra simulated controls"):
            self.assertIn(text.casefold(), self.html.casefold())
        for path in ("src/bean_strategy_lab.py", "src/bean_research_supervisor.py",
                     "src/bean_five_minute.py", "src/bean_policy.py"):
            self.assertIn("https://github.com/danieloculus0-bot/AIscend/blob/main/" + path,
                          self.markup.links)
        self.assertIn("#research-updates", self.markup.links)

    def test_nav_mascot_no_longer_cropped(self):
        self.assertIn(".brand img{width:51px;height:60px;object-fit:contain", self.html)
        self.assertIn("flex-shrink:0", self.html)
        self.assertIn('src="./bean-official.webp"', self.html)

    def test_only_one_complete_html_document_with_no_rendered_script_tail(self):
        # A duplicate <script> block once appeared after </html> and was
        # rendered verbatim at the bottom on both mobile and desktop.
        self.assertEqual(self.html.count("</html>"), 1)
        self.assertEqual(self.html.count("</body>"), 1)
        self.assertNotIn("const rand=()=>", self.html)
        self.assertRegex(self.html, r"</body>\s*</html>\s*\Z")
        self.assertFalse(self.html.split("</html>", 1)[1].strip())

    @unittest.skipUnless(shutil.which("node"), "Node.js needed for browser script syntax check")
    def test_inline_browser_javascript_parses(self):
        scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", self.html)
        self.assertEqual(len(scripts), 1)
        for index, script in enumerate(scripts):
            with self.subTest(script=index):
                out = subprocess.run([shutil.which("node"), "--check"],
                                     input=script, text=True, capture_output=True)
                self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('function drawPet(){', scripts[0])


if __name__ == '__main__':
    unittest.main()
