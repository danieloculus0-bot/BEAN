"""Offline regression tests for canonical links across the public BEAN ecosystem."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import unittest

ROOT = Path(__file__).resolve().parents[1] / "docs"
ERP = "https://danieloculus0-bot.github.io/Axiom_Beta/erp/"
WORKSHOP = "https://danieloculus0-bot.github.io/BEAN/portfolio/"
PAGES = (
    "index.html",
    "portfolio/index.html",
    "axiom.html",
    "aiscend.html",
    "portfolio/ez-fair/index.html",
    "portfolio/ez-office/index.html",
    "portfolio/bean-learning/index.html",
    "bean-demo/index.html",
    "research-lab.html",
    "for-ai-developers.html",
    "rubiks-cube.html",
    "portfolio/axiom/index.html",
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.refreshes = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag == "meta" and a.get("http-equiv", "").lower() == "refresh":
            self.refreshes.append(a.get("content", ""))


class EcosystemNavigationTests(unittest.TestCase):
    def page(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def links(self, name):
        parser = Links()
        parser.feed(self.page(name))
        return parser

    def test_every_public_entry_point_links_to_the_real_erp(self):
        for name in PAGES:
            with self.subTest(page=name):
                self.assertIn(ERP, self.links(name).links)

    def test_home_and_workshop_are_bidirectionally_discoverable(self):
        home = self.links("index.html").links
        directory = self.links("portfolio/index.html").links
        self.assertIn("./portfolio/", home)
        self.assertIn("../", directory)
        self.assertIn(ERP, directory)

    def test_user_approved_axiom_lab_is_preserved_and_connected(self):
        lab = self.page("portfolio/axiom/index.html")
        self.assertNotIn('http-equiv="refresh"', lab)
        self.assertNotIn("window.location.replace(", lab)
        self.assertIn("Command Center", lab)
        self.assertIn("Job Passport", lab)
        self.assertIn("Cost / Estimate", lab)
        self.assertIn("Inspection / FAI", lab)
        self.assertIn("Evidence Ledger", lab)
        self.assertIn('class="shell"', lab)
        self.assertIn('class="side"', lab)
        self.assertIn(ERP, self.links("portfolio/axiom/index.html").links)
        self.assertIn(WORKSHOP, self.links("portfolio/axiom/index.html").links)
        self.assertIn('axiom/', self.links("portfolio/index.html").links)
        self.assertIn('./portfolio/axiom/', self.links("axiom.html").links)

    def test_navigation_does_not_steal_record_specific_routes(self):
        # External ecosystem links must be ordinary anchors, never an ERP
        # hash route or a script that touches the browser-local record store.
        for name in PAGES:
            with self.subTest(page=name):
                links = self.links(name).links
                self.assertFalse(any(url.startswith(ERP + "#") for url in links))
                self.assertFalse(any(url.startswith("javascript:") for url in links))

    def test_bean_core_demo_is_reachable_without_fake_service(self):
        self.assertIn("./bean-demo/", self.links("index.html").links)
        self.assertIn("../bean-demo/", self.links("portfolio/index.html").links)
        page = self.page("bean-demo/index.html")
        self.assertIn("research/github_brain/manifest.json", page)
        self.assertIn("bean.github.request.v1", page)
        # The public demo has real device-local IndexedDB, an offline app shell,
        # and controlled export/import, not cookie-based or public user storage.
        self.assertIn('src="./device-ui.mjs"', page)
        self.assertIn('href="./manifest.webmanifest"', page)
        self.assertIn('id="local-note"', page)
        self.assertIn('id="export-device"', page)
        self.assertIn('id="clear-device"', page)
        self.assertIn('id="import-file"', page)
        for resource in ("device-ui.mjs", "device-memory.mjs",
                         "sw.js", "manifest.webmanifest"):
            self.assertTrue((ROOT / "bean-demo" / resource).is_file(), resource)
        storage = (ROOT / "bean-demo" / "device-memory.mjs").read_text()
        self.assertIn("indexedDBFactory.open(DB_NAME", storage)
        self.assertIn("verifyPublicManifest", storage)
        self.assertIn("replayLedger", storage)
        self.assertNotIn("localStorage.setItem", storage)
        self.assertIn("dictionary-patch ledger", page.lower())
        self.assertIn("https://danieloculus0-bot.github.io/Axiom_Beta/erp/",
                      self.links("bean-demo/index.html").links)

    def test_canonical_app_link_is_https(self):
        self.assertEqual((urlparse(ERP).scheme, urlparse(ERP).netloc),
                         ("https", "danieloculus0-bot.github.io"))


if __name__ == "__main__":
    unittest.main()
