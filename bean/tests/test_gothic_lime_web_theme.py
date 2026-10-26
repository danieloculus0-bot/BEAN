"""Public BEAN site follows the same charcoal-and-lime token contract."""
from pathlib import Path

def test_public_theme_and_mascot_are_present():
    html = (Path(__file__).resolve().parents[2] / "docs" / "index.html").read_text(encoding="utf-8")
    # A later black-canvas override is intentional; assert the effective
    # project palette rather than the superseded charcoal tokens.
    for token in ("--bg:#050607", "--surface:#111417", "--raised:#101214",
                  "--line:#212325", "--accent:#79DE4B", "--focus:#79DE4B",
                  "html{background:#050607}"):
        assert token in html
    assert "bean-official.webp" in html
    assert "prefers-reduced-motion:reduce" in html
    assert "--orange:" not in html
