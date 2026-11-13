"""Public-safe reviewable SVG pipeline regression tests."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts.build_bean_draw_gallery import curate, validate_svg
from scripts.run_bean_draw_fixture import make_demo


def test_gallery_captures_real_core_fixture_and_is_idempotent(tmp_path):
    source = tmp_path / "generated"
    site = tmp_path / "site" / "bean-draw"
    result = make_demo(source)
    assert result["attempts"] == 2
    assert all(Path(row["svg"]).exists() for row in result["history"])
    for attempt in (1, 2):
        metadata = json.loads((source / ("attempt_%02d.json" % attempt)).read_text())
        svg = (source / ("attempt_%02d.svg" % attempt)).read_bytes()
        assert metadata["schema"] == "bean.draw.attempt.v1"
        assert metadata["provider_kind"] == "synthetic_fixture"
        assert metadata["journal_tip"]
        assert metadata["svg_sha256"] == sha256(svg).hexdigest()
        assert metadata["independent_visual_verification"] is False

    first = curate(source, site)
    assert first["added"] == 2
    assert first["entries"] == 2
    second = curate(source, site)
    assert second["added"] == 0
    index = json.loads((site / "index.json").read_text())
    assert len(index["entries"]) == 2
    assert all(entry["origin"] == "synthetic_fixture" for entry in index["entries"])
    assert all((site / entry["svg"]).is_file() for entry in index["entries"])
    assert all(entry["independent_visual_verification"] is False
               for entry in index["entries"])
    for entry in index["entries"]:
        svg = (site / entry["svg"]).read_bytes()
        validate_svg(svg)
        assert entry["sha256"] == sha256(svg).hexdigest()


def test_gallery_rejects_tampered_svg(tmp_path):
    source = tmp_path / "source"
    make_demo(source)
    (source / "attempt_01.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="10" cy="10" r="3"/></svg>')
    with pytest.raises(ValueError, match="no longer matches"):
        curate(source, tmp_path / "site")


@pytest.mark.parametrize("svg", [
    b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://test.example/a"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
    b'<not-svg></not-svg>',
])
def test_gallery_rejects_active_svg(svg):
    with pytest.raises(ValueError):
        validate_svg(svg)


def test_missing_sidecars_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="No BEAN sketch attempt"):
        curate(tmp_path, tmp_path / "site")
