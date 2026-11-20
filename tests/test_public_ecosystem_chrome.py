"""The BEAN public ecosystem always exposes a direct BEAN home and project directory route."""
from pathlib import Path
import unittest

DOCS = Path(__file__).resolve().parents[1] / "docs"
HOME = "https://danieloculus0-bot.github.io/BEAN/"
WORKSHOP = HOME + "portfolio/"
STATUS = HOME + "status.html"
AXIOM = "https://danieloculus0-bot.github.io/Axiom_Beta/erp/"

class EcosystemNavigationChromeTest(unittest.TestCase):
    def test_each_public_html_has_a_single_consistent_network_navigation(self):
        files = sorted(DOCS.rglob("*.html"))
        self.assertGreaterEqual(len(files), 18)
        for path in files:
            with self.subTest(page=str(path.relative_to(DOCS))):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(source.count('data-bean-ecosystem-nav="v1"'), 1)
                self.assertIn('aria-label="BEAN ecosystem navigation"', source)
                self.assertIn(f'href="{HOME}"', source)
                self.assertIn(f'href="{WORKSHOP}"', source)
                self.assertIn(f'href="{STATUS}"', source)
                self.assertIn(f'href="{AXIOM}"', source)
                self.assertNotIn('class="bean-nov20-status"', source)
                self.assertLess(source.index('data-bean-ecosystem-nav="v1"'), source.lower().find("</body>"))

    def test_central_navigation_css_remains_available(self):
        css = (DOCS / "ecosystem-nav.css").read_text(encoding="utf-8")
        self.assertIn(".bean-net", css)
        self.assertIn(".bean-net-float", css)

if __name__ == "__main__":
    unittest.main()
