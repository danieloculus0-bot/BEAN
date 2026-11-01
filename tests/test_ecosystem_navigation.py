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

    def test_stale_axiom_lab_redirects_instead_of_repeating_the_application(self):
        obsolete = self.page("portfolio/axiom/index.html")
        self.assertIn('content="0;url=' + ERP + '"', obsolete)
        self.assertIn('window.location.replace(', obsolete)
        self.assertNotIn("quoteTotal", obsolete)
        self.assertNotIn("inspectionSummary", obsolete)
        self.assertIn(WORKSHOP, self.links("portfolio/axiom/index.html").links)
        self.assertNotIn('href="./axiom/"', self.page("portfolio/index.html"))
        self.assertNotIn('href="./portfolio/axiom/"', self.page("axiom.html"))

    def test_navigation_does_not_steal_record_specific_routes(self):
        # External ecosystem links must be ordinary anchors, never an ERP
        # hash route or a script that touches the browser-local record store.
        for name in PAGES:
            with self.subTest(page=name):
                links = self.links(name).links
                self.assertFalse(any(url.startswith(ERP + "#") for url in links))
                self.assertFalse(any(url.startswith("javascript:") for url in links))

    def test_canonical_app_link_is_https(self):
        self.assertEqual((urlparse(ERP).scheme, urlparse(ERP).netloc),
                         ("https", "danieloculus0-bot.github.io"))


if __name__ == "__main__":
    unittest.main()
