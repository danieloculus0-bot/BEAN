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

    def test_showcase_uses_maintained_browser_suite_and_attendance(self):
        html = self.page("portfolio/index.html")
        showcase = html.split('<section id="demos" class="wrap">', 1)[1].split("</section>", 1)[0]
        self.assertEqual(showcase.count('class="demo"'), 4)
        for marker in ("Open Axiom ERP", "Open EZ CAM workbench", "Open EZ-Office suite",
                       "Open EZ Attendance", "https://danieloculus0-bot.github.io/EZ-Attendance/",
                       "https://danieloculus0-bot.github.io/EZ-CAM/", 'href="ez-office/"'):
            self.assertIn(marker, showcase)
        for retired in ('href="ez-fair/"', 'href="../aiscend.html"',
                        "https://danieloculus0-bot.github.io/EZstimate/",
                        "https://danieloculus0-bot.github.io/64-/", "https://danieloculus0-bot.github.io/FUN/"):
            self.assertNotIn(retired, showcase)
        self.assertNotIn('href="https://danieloculus0-bot.github.io/64-/"', html)

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
