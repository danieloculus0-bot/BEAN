"""Static contract for the shipped EZ-Office demo in BEAN Workshop."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "docs"
OFFICE = PAGES / "portfolio" / "ez-office"
TOOLS = ("writer", "sheets", "slides", "media", "mail")


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        for name in ("href", "src"):
            if name in props and tag in ("link", "script", "img"):
                self.refs.append(props[name])


def test_office_demo_is_locally_complete_and_in_menu():
    page = (OFFICE / "index.html").read_text(encoding="utf-8")
    assert "<title>EZ-Office" in page
    assert 'href="../"' in page  # Back to Workshop, not BEAN agent integration
    assert 'src="shell.js?v=native-media-03"' in page
    assert 'src="lib/office-export.js?v=native-media-03"' in page
    assert 'src="lib/office-import.js?v=native-media-03"' in page
    assert (OFFICE / "lib/office-export.js").is_file()
    assert (OFFICE / "lib/office-import.js").is_file()
    assert 'href="styles.css?v=native-media-03"' in page
    assets = Assets()
    assets.feed(page)
    for path in assets.refs:
        assert not path.startswith(("http://", "https://")), path
        assert (OFFICE / path.partition("?")[0]).is_file(), path

    shell = (OFFICE / "shell.js").read_text(encoding="utf-8")
    assert 'script.src="apps/"+id+".js?v=native-media-03"' in shell
    assert "const disposers=[]" in shell
    for tool in TOOLS:
        assert f'data-tool="{tool}"' in page
        script = OFFICE / "apps" / f"{tool}.js"
        assert script.is_file()
        assert script.stat().st_size > 1000
        assert f'EZOffice.register("{tool}"' in script.read_text(encoding="utf-8")


def test_workshop_and_bean_home_link_working_suite():
    workshop = (PAGES / "portfolio" / "index.html").read_text(encoding="utf-8")
    homepage = (PAGES / "index.html").read_text(encoding="utf-8")
    assert workshop.count('href="ez-office/"') >= 3
    assert "EZ-Office" in workshop
    assert '<strong>19</strong><span>Catalogued projects</span>' in workshop
    assert 'n===19?' in workshop
    assert 'Showing all 19 projects' in workshop
    assert "data-category=\"platform\" data-search=\"ez office" in workshop
    assert 'href="./portfolio/ez-office/"' in homepage
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://danieloculus0-bot.github.io/BEAN/portfolio/ez-office/" in readme
    assert "DOCX/XLSX/PPTX" in readme
