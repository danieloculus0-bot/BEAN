"""Protect the current charcoal-green BEAN homepage palette and mascot."""
from pathlib import Path


def test_public_theme_and_mascot_are_present():
    html = (Path(__file__).resolve().parents[2] / "docs" / "index.html").read_text(
        encoding="utf-8"
    )
    for token in ("--bg:#0b100e", "--card:#152019", "--green:#a6ed75",
                  "color-scheme:dark", "a:focus-visible",
                  "prefers-reduced-motion:reduce"):
        assert token in html
    assert html.count('src="./bean-official.webp"') == 2
    assert 'alt="BEAN project mascot"' in html
    assert "--orange:" not in html
