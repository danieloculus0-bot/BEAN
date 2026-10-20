"""Public BEAN site follows the same charcoal-and-lime token contract."""
from pathlib import Path

def test_public_theme_and_mascot_are_present():
    html = (Path(__file__).resolve().parents[2] / "docs" / "index.html").read_text(encoding="utf-8")
    for token in ("--bg:#0F1113", "--surface:#1A1D20", "--raised:#22282A",
                  "--line:#303A3B", "--accent:#79DE4B", "--focus:#79DE4B"):
        assert token in html
    assert "bean-official.webp" in html
    assert "prefers-reduced-motion:reduce" in html
    assert "--orange:" not in html
