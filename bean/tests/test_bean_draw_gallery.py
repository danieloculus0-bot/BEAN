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


def test_checked_in_showcase_art_matches_committed_receipts():
    """Static Pages examples must be the exact CI-generated fixture bytes."""
    import hashlib
    root = Path(__file__).resolve().parents[2] / "docs" / "bean-draw"
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    assert index["schema"] == "bean.draw.gallery.v1"
    assert len(index["entries"]) >= 2
    for row in index["entries"]:
        svg = root / row["svg"]
        descriptor = json.loads((root / row["metadata"]).read_text(encoding="utf-8"))
        raw = svg.read_bytes()
        validate_svg(raw)
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
        assert descriptor["sha256"] == row["sha256"]
        assert descriptor["origin"] == row["origin"]
        assert row["independent_visual_verification"] is False


@pytest.mark.parametrize("svg", [
    b'<!DOCTYPE svg [<!ENTITY x "expanded">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
    b'<?xml-stylesheet href="https://example.org/a.css"?><svg xmlns="http://www.w3.org/2000/svg"/>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><circle xmlns="urn:foreign"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg" width="9999999999"/>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="nan"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="u\\72l(//example.org/a)"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1e999 1e999"/>',
])
def test_svg_security_before_rasterization(svg):
    with pytest.raises(ValueError):
        validate_svg(svg)


def test_curator_rechecks_existing_assets_and_index(tmp_path):
    source, site = tmp_path / "source", tmp_path / "site"
    make_demo(source)
    curate(source, site)
    listing = json.loads((site / "index.json").read_text())
    (site / listing["entries"][0]["svg"]).write_text("tampered")
    with pytest.raises(ValueError):
        curate(source, site)


def test_duplicate_index_entries_are_rejected(tmp_path):
    source, site = tmp_path / "source", tmp_path / "site"
    make_demo(source)
    curate(source, site)
    index = site / "index.json"
    listing = json.loads(index.read_text())
    listing["entries"].append(listing["entries"][0])
    index.write_text(json.dumps(listing))
    with pytest.raises(ValueError, match="Duplicate"):
        curate(source, site)


def test_fixture_cannot_claim_live_execution(tmp_path):
    source = tmp_path / "source"
    make_demo(source)
    meta = source / "attempt_01.json"
    row = json.loads(meta.read_text())
    row["execution_mode"] = "live_model"
    meta.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="Fixture mislabeled"):
        curate(source, tmp_path / "site")


def reviewed_transport_case(source):
    """Synthetic receipt transport case, never a claim of live model output."""
    from io import BytesIO
    pytest.importorskip("PIL.Image")
    try:
        import cairosvg
    except (ImportError, OSError):
        pytest.skip("Optional CairoSVG preview backend unavailable")
    from bean.creativity.artifacts import rasterize
    from scripts.build_bean_draw_gallery import REVIEW_SCHEMA
    make_demo(source)
    run = {"schema": "bean.draw.run.v1", "run_id": "transport-test", "history": []}
    for meta in source.glob("attempt_[0-9][0-9].json"):
        row = json.loads(meta.read_text())
        row.update(provider_kind="ollama", execution_mode="live_model",
                   source_git_sha="a" * 40, created_at_utc="2026-11-19T00:00:00Z",
                   subject_source="autonomous", run_id="transport-test",
                   verification_state="artifacts_verified")
        name = meta.stem + ".png"
        preview = rasterize(source / row["svg_file"], source / name)
        row.update(png_file=name, **preview)
        meta.write_text(json.dumps(row))
        run["history"].append({"attempt": row["attempt"], "metadata_sha256": sha256(meta.read_bytes()).hexdigest(),
                               "sha256": row["svg_sha256"], "png_sha256": row["png_sha256"]})
    (source / "run.json").write_text(json.dumps(run))
    review = source / "public-review.json"
    report = {"schema": REVIEW_SCHEMA, "reviewer": "synthetic-test-only",
              "reviewed_at_utc": "2026-11-19T00:00:00Z", "public_safe": True,
              "files": {p.name: sha256(p.read_bytes()).hexdigest()
                        for p in source.iterdir() if p.is_file()}}
    review.write_text(json.dumps(report))
    return review


def test_public_model_records_require_hash_bound_review(tmp_path):
    source, site = tmp_path / "source", tmp_path / "site"
    review = reviewed_transport_case(source)
    with pytest.raises(ValueError, match="explicit public-safe"):
        curate(source, site)
    report = json.loads(review.read_text())
    report["files"]["attempt_01.svg"] = "0" * 64
    review.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="exact artifact bytes"):
        curate(source, site, review=review)
    assert not (site / "index.json").exists()


def test_reviewed_transport_preserves_exact_receipts_and_png(tmp_path):
    source, site = tmp_path / "source", tmp_path / "site"
    review = reviewed_transport_case(source)
    result = curate(source, site, review=review)
    assert result["added"] == 2
    listing = json.loads((site / "index.json").read_text())
    for entry in listing["entries"]:
        assert entry["origin"] == "live_model_artifact_verified"
        assert entry["independent_visual_verification"] is False
        original = source / ("attempt_%02d.json" % entry["attempt"])
        assert (site / entry["attempt_receipt"]).read_bytes() == original.read_bytes()
        assert sha256((site / entry["png"]).read_bytes()).hexdigest() == entry["png_sha256"]
        assert sha256((site / entry["run_receipt"]).read_bytes()).hexdigest() == entry["run_receipt_sha256"]
    assert curate(source, site, review=review)["added"] == 0
    (site / listing["entries"][0]["png"]).unlink()
    with pytest.raises(ValueError):
        curate(source, site, review=review)


def test_live_transport_rejects_incomplete_identity(tmp_path):
    source = tmp_path / "source"
    review = reviewed_transport_case(source)
    meta = source / "attempt_01.json"
    row = json.loads(meta.read_text())
    row["source_git_sha"] = "local-unverified"
    meta.write_text(json.dumps(row))
    report = json.loads(review.read_text())
    report["files"][meta.name] = sha256(meta.read_bytes()).hexdigest()
    review.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="incomplete provenance|does not bind"):
        curate(source, tmp_path / "site", review=review)


def test_run_receipt_must_bind_sidecar_and_artifact_hashes(tmp_path):
    source = tmp_path / "source"
    review = reviewed_transport_case(source)
    run_path = source / "run.json"
    run = json.loads(run_path.read_text())
    run["history"][0]["metadata_sha256"] = "f" * 64
    run_path.write_text(json.dumps(run))
    report = json.loads(review.read_text())
    report["files"]["run.json"] = sha256(run_path.read_bytes()).hexdigest()
    review.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="does not bind"):
        curate(source, tmp_path / "site", review=review)


def test_index_paths_cannot_escape_gallery(tmp_path):
    source, site = tmp_path / "source", tmp_path / "site"
    make_demo(source)
    curate(source, site)
    listing = json.loads((site / "index.json").read_text())
    listing["entries"][0]["svg"] = "../private.svg"
    (site / "index.json").write_text(json.dumps(listing))
    with pytest.raises(ValueError, match="Unsafe gallery"):
        curate(source, site)


def test_hashes_alone_cannot_certify_a_fake_preview(tmp_path):
    source = tmp_path / "source"
    review = reviewed_transport_case(source)
    from PIL import Image
    image_path = source / "attempt_01.png"
    Image.new("RGB", (512, 512), "white").save(image_path)
    meta_path = source / "attempt_01.json"
    row = json.loads(meta_path.read_text())
    row["png_sha256"] = sha256(image_path.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(row))
    run_path = source / "run.json"
    run = json.loads(run_path.read_text())
    entry = next(e for e in run["history"] if e["attempt"] == 1)
    entry.update(png_sha256=row["png_sha256"], metadata_sha256=sha256(meta_path.read_bytes()).hexdigest())
    run_path.write_text(json.dumps(run))
    report = json.loads(review.read_text())
    report["files"].update({p.name: sha256(p.read_bytes()).hexdigest()
                             for p in (image_path, meta_path, run_path)})
    review.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="does not depict"):
        curate(source, tmp_path / "site", review=review)
