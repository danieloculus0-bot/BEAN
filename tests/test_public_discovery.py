"""Offline search-discovery regression checks for the published BEAN project site.

These checks verify source metadata and sitemap coverage, not actual Google/Bing indexing.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote
import json
import re
import unittest
import xml.etree.ElementTree as ET

DOCS = Path(__file__).resolve().parents[1] / "docs"
BASE = "https://danieloculus0-bot.github.io/BEAN/"
REQUIRED = (
    "", "for-ai-developers.html", "research-lab.html", "bean-draw/",
    "rubiks-cube.html", "bean-demo/", "portfolio/",
    "portfolio/bean-learning/", "portfolio/ez-fair/",
    "axiom.html", "aiscend.html", "beanrivet/",
)
NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class HeadMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head = True
        self.in_title = False
        self.title = ""
        self.meta = {}
        self.canonicals = []

    def handle_starttag(self, tag, attrs):
        if not self.in_head:
            return
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key:
                self.meta[key.lower()] = attrs.get("content", "")
        if tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonicals.append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "head":
            self.in_head = False

    def handle_data(self, data):
        if self.in_head and self.in_title:
            self.title += data


def source_path(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "danieloculus0-bot.github.io":
        raise ValueError("not the expected HTTPS GitHub Pages host")
    if not parsed.path.startswith("/BEAN/") or parsed.query or parsed.fragment:
        raise ValueError("not an absolute canonical BEAN page")
    relative = unquote(parsed.path[len("/BEAN/"):])
    if ".." in Path(relative).parts or "\\" in relative:
        raise ValueError("invalid relative page path")
    path = relative + "index.html" if not relative or relative.endswith("/") else relative
    return DOCS / path


class PublicDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sitemap = ET.fromstring((DOCS / "sitemap.xml").read_bytes())
        cls.urls = [node.text for node in cls.sitemap.findall(f"{NAMESPACE}url/{NAMESPACE}loc")]

    def test_sitemap_is_complete_unique_and_local(self):
        self.assertEqual(self.sitemap.tag, f"{NAMESPACE}urlset")
        self.assertEqual(len(self.urls), len(set(self.urls)), "duplicate sitemap entries")
        self.assertTrue(set(BASE + page for page in REQUIRED).issubset(self.urls))
        for url in self.urls:
            with self.subTest(url=url):
                self.assertTrue(source_path(url).is_file(), url)

    def test_every_sitemap_page_is_self_canonical_and_described(self):
        titles = {}
        for url in self.urls:
            with self.subTest(url=url):
                parser = HeadMeta()
                parser.feed(source_path(url).read_text(encoding="utf-8"))
                self.assertEqual(parser.canonicals, [url])
                self.assertGreater(len(parser.title.strip()), 12)
                self.assertGreater(len(parser.meta.get("description", "").strip()), 50)
                self.assertNotIn("noindex", parser.meta.get("robots", "").lower())
                titles.setdefault(parser.title.strip(), []).append(url)
        self.assertEqual({name: urls for name, urls in titles.items() if len(urls) > 1}, {})

    def test_home_identifies_project_and_publishes_parseable_source_metadata(self):
        homepage = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn("Behavior Enabled Avatar Node", homepage)
        self.assertIn("model-independent", homepage)
        self.assertIn("https://github.com/danieloculus0-bot/BEAN", homepage)
        scripts = re.findall(
            r'<script\\s+type="application/ld\\+json"[^>]*>(.*?)</script>',
            homepage, re.DOTALL | re.IGNORECASE
        )
        self.assertTrue(scripts, "homepage must contain JSON-LD structured data")
        docs = [json.loads(script) for script in scripts]
        entities = [entity for doc in docs for entity in doc.get("@graph", [doc])]
        self.assertIn("SoftwareSourceCode", [entity.get("@type") for entity in entities])
        self.assertTrue(any(
            entity.get("codeRepository") == "https://github.com/danieloculus0-bot/BEAN"
            for entity in entities
        ))

    def test_research_page_is_not_canonicalized_to_homepage(self):
        parser = HeadMeta()
        parser.feed((DOCS / "research-lab.html").read_text(encoding="utf-8"))
        self.assertEqual(parser.canonicals, [BASE + "research-lab.html"])


if __name__ == "__main__":
    unittest.main()
