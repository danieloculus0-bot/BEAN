#!/usr/bin/env python3
"""Curate reviewed BEAN drawings; preserve fixtures as explicitly synthetic.

Artifact verification checks bytes, not artistic quality or model authenticity.
Public model output requires a review manifest bound to the exact published files.
"""
from __future__ import annotations

import argparse
from io import BytesIO
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SCHEMA = "bean.draw.gallery.v1"
SOURCE_SCHEMA = "bean.draw.attempt.v1"
REVIEW_SCHEMA = "bean.draw.public-review.v1"
SVG_NS = "http://www.w3.org/2000/svg"
ALLOWED_TAGS = {"svg", "g", "defs", "circle", "line", "rect", "polyline"}
ALLOWED_ATTRS = {
    "width", "height", "viewBox", "version", "x", "y", "x1", "y1",
    "x2", "y2", "cx", "cy", "r", "points", "stroke", "stroke-width",
    "stroke-linecap", "stroke-linejoin", "fill", "fill-opacity", "opacity",
    "id",
}
MAX_SVG_BYTES = 250000


def validate_svg(raw: bytes) -> None:
    """Reject active/external XML before any rasterizer sees these bytes."""
    if not raw or len(raw) > MAX_SVG_BYTES:
        raise ValueError("SVG is empty or oversized")
    lower = raw.lower()
    if any(token in lower for token in (b"<!doctype", b"<!entity", b"<?xml-stylesheet")):
        raise ValueError("SVG declarations and stylesheets are not allowed")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("SVG is not well-formed XML") from exc
    if root.tag != "{" + SVG_NS + "}svg":
        raise ValueError("Not a namespaced SVG document")
    elements = list(root.iter())
    if len(elements) > 120:
        raise ValueError("Excessive SVG elements")
    for el in elements:
        if not el.tag.startswith("{" + SVG_NS + "}"):
            raise ValueError("Unapproved SVG namespace")
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ALLOWED_TAGS:
            raise ValueError("Unapproved SVG element: " + tag)
        if (el.text and el.text.strip()) or (el.tail and el.tail.strip()):
            raise ValueError("Embedded SVG text is not allowed")
        if len(el.attrib) > 24:
            raise ValueError("Excessive SVG attributes")
        for key, value in el.attrib.items():
            if key not in ALLOWED_ATTRS or len(value) > 2000:
                raise ValueError("Unapproved SVG attribute: " + key)
            if any(s in value.lower() for s in ("url(", "javascript:", "data:", "http:")):
                raise ValueError("External SVG reference not allowed")
            if key in {"fill", "stroke"} and not re.fullmatch(r"(?:[a-zA-Z]{1,24}|#[a-fA-F0-9]{3,8})", value):
                raise ValueError("Unsupported SVG paint value")
            if key in {"points", "viewBox"}:
                try:
                    numbers = [float(part) for part in re.split(r"[\s,]+", value.strip())]
                except ValueError as exc:
                    raise ValueError("Invalid SVG numeric list") from exc
                if (not numbers or any(not math.isfinite(n) or abs(n) > 4096 for n in numbers)
                        or key == "viewBox" and len(numbers) != 4
                        or key == "points" and (len(numbers) % 2 or len(numbers) > 80)):
                    raise ValueError("Unbounded SVG numeric list")
            if key in {"width", "height", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "stroke-width", "opacity", "fill-opacity"}:
                try:
                    number = float(value)
                except ValueError as exc:
                    raise ValueError("Non-numeric SVG coordinate") from exc
                if not math.isfinite(number) or abs(number) > 4096:
                    raise ValueError("Unbounded SVG coordinate")
    for attr in ("width", "height"):
        if attr in root.attrib and not 0 < float(root.attrib[attr]) <= 4096:
            raise ValueError("Invalid SVG canvas size")


def _validate_png(raw):
    if not raw or len(raw) > 5000000:
        raise ValueError("PNG empty or oversized")
    from PIL import Image
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format != "PNG" or max(image.size) > 4096:
                raise ValueError("Invalid PNG preview")
            image.verify()
    except (OSError, SyntaxError) as exc:
        raise ValueError("Invalid PNG preview") from exc


def _verify_preview(svg, png):
    # A hash proves preserved bytes, not that a PNG depicts the linked SVG.
    import cairosvg
    from PIL import Image, ImageChops
    rendered = cairosvg.svg2png(bytestring=svg, unsafe=False, output_width=512,
                               output_height=512, background_color="white")
    with Image.open(BytesIO(png)) as actual, Image.open(BytesIO(rendered)) as expected:
        if actual.size != expected.size or ImageChops.difference(
                actual.convert("RGB"), expected.convert("RGB")).getbbox() is not None:
            raise ValueError("PNG preview does not depict the recorded SVG")


def _digest(raw):
    return sha256(raw).hexdigest()


def _json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _file(folder, filename):
    if (not isinstance(filename, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]+", filename)
            or filename in (".", "..")):
        raise ValueError("Unsafe artifact filename")
    path = folder / filename
    if path.is_symlink() or not path.is_file():
        raise ValueError("Artifact referenced by receipt does not exist")
    return path


def _asset(site, name, identity, suffix):
    expected = "entries/" + identity + suffix
    if name != expected:
        raise ValueError("Unsafe gallery index path")
    return _file(site / "entries", identity + suffix)


def validate_index(site: Path, listing: dict) -> None:
    """Read back every indexed asset, including entries skipped on reruns."""
    if listing.get("schema") != SCHEMA or not isinstance(listing.get("entries"), list):
        raise ValueError("Existing gallery index has an unknown schema")
    seen = set()
    for row in listing["entries"]:
        key = row.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{20}", key) or key in seen:
            raise ValueError("Duplicate or invalid gallery identity")
        seen.add(key)
        svg = _asset(site, row.get("svg"), key, ".svg").read_bytes()
        validate_svg(svg)
        if _digest(svg) != row.get("sha256"):
            raise ValueError("Existing gallery SVG hash mismatch")
        descriptor = json.loads(_asset(site, row.get("metadata"), key, ".json").read_bytes())
        if descriptor != row:
            raise ValueError("Gallery index and descriptor disagree")
        if row.get("provider_kind") == "synthetic_fixture" and row.get("origin") != "synthetic_fixture":
            raise ValueError("Fixture mislabeled as live artwork")
        for field, hash_field, suffix in (("png", "png_sha256", ".png"),
                                         ("attempt_receipt", "attempt_receipt_sha256", ".attempt.json"),
                                         ("run_receipt", "run_receipt_sha256", ".run.json"),
                                         ("public_review", "public_review_sha256", ".review.json")):
            if row.get(field):
                raw = _asset(site, row[field], key, suffix).read_bytes()
                if field == "png":
                    _validate_png(raw)
                if _digest(raw) != row.get(hash_field):
                    raise ValueError("Existing gallery artifact hash mismatch: " + field)
        if row.get("origin") == "live_model_artifact_verified" and not all(row.get(f) for f in
                ("png", "attempt_receipt", "run_receipt", "public_review")):
            raise ValueError("Verified live entry is missing evidence")


def _review_manifest(review):
    if review is None:
        return None
    report = json.loads(Path(review).read_bytes())
    if (report.get("schema") != REVIEW_SCHEMA or report.get("public_safe") is not True
            or not isinstance(report.get("reviewer"), str) or not report["reviewer"].strip()
            or not isinstance(report.get("files"), dict)):
        raise ValueError("Invalid public-safe review manifest")
    _utc(report.get("reviewed_at_utc"))
    return report


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("Missing UTC provenance timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC provenance timestamp") from exc
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("UTC provenance timestamp required")


def curate(source: Path, site: Path, *, review: Path | None = None) -> dict:
    source, site = Path(source), Path(site)
    metas = sorted(source.glob("attempt_[0-9][0-9].json"))
    if not metas:
        raise ValueError("No BEAN sketch attempt sidecars found")
    output_index = site / "index.json"
    listing = json.loads(output_index.read_bytes()) if output_index.exists() else {"schema": SCHEMA, "entries": []}
    validate_index(site, listing)
    previous = {item["id"]: item for item in listing["entries"]}
    report = _review_manifest(review)
    pending = []
    for metadata in metas:
        raw_meta = _file(source, metadata.name).read_bytes()
        row = json.loads(raw_meta)
        if row.get("schema") != SOURCE_SCHEMA:
            raise ValueError("Unknown drawing receipt schema")
        attempt = row.get("attempt")
        if type(attempt) is not int or not 1 <= attempt <= 99:
            raise ValueError("Invalid attempt")
        if row.get("svg_file") is None:
            continue
        expected_name = "attempt_%02d.svg" % attempt
        if row["svg_file"] != expected_name:
            raise ValueError("Unsafe or inconsistent drawing filename")
        raw = _file(source, expected_name).read_bytes()
        validate_svg(raw)
        digest = _digest(raw)
        if row.get("svg_sha256") != digest:
            raise ValueError("Drawing no longer matches BEAN's journal receipt")
        for name in ("task_ref", "subject", "status", "model_id", "provider_kind", "journal_tip"):
            if not isinstance(row.get(name), str) or not 0 < len(row[name]) <= 300:
                raise ValueError("Missing or unbounded drawing provenance: " + name)
        urls = row.get("reference_urls", [])
        if not isinstance(urls, list) or len(urls) > 12 or any(
                not isinstance(url, str) or len(url) > 600 or not url.startswith("https://") for url in urls):
            raise ValueError("Unapproved reference URL")
        fixture = row["provider_kind"] == "synthetic_fixture"
        if fixture and row.get("execution_mode", "synthetic_fixture") != "synthetic_fixture":
            raise ValueError("Fixture mislabeled as live artwork")
        if not fixture and report is None:
            raise ValueError("Model artwork requires an explicit public-safe review manifest")
        files = {metadata.name: raw_meta, expected_name: raw}
        png = run_raw = None
        if row.get("png_file"):
            if row["png_file"] != "attempt_%02d.png" % attempt:
                raise ValueError("Unsafe PNG filename")
            png = _file(source, row["png_file"]).read_bytes()
            _validate_png(png)
            if _digest(png) != row.get("png_sha256"):
                raise ValueError("PNG missing or hash mismatch")
            files[row["png_file"]] = png
        run_name = row.get("run_receipt") or ("run.json" if (source / "run.json").is_file() else None)
        if run_name:
            run_raw = _file(source, run_name).read_bytes()
            if row.get("run_receipt_sha256") and _digest(run_raw) != row["run_receipt_sha256"]:
                raise ValueError("Run receipt hash mismatch")
            run_data = json.loads(run_raw)
            if row.get("execution_mode") == "live_model":
                matching = [h for h in run_data.get("history", []) if h.get("attempt") == attempt]
                if (run_data.get("schema") != "bean.draw.run.v1"
                        or run_data.get("run_id") != row.get("run_id") or len(matching) != 1
                        or matching[0].get("metadata_sha256") != _digest(raw_meta)
                        or matching[0].get("sha256") != digest
                        or matching[0].get("png_sha256") != row.get("png_sha256")):
                    raise ValueError("Run receipt does not bind this attempt")
            files[run_name] = run_raw
        if not fixture:
            if png is not None:
                _verify_preview(raw, png)
            if any(report["files"].get(name) != _digest(data) for name, data in files.items()):
                raise ValueError("Public review does not cover exact artifact bytes")
            if row.get("execution_mode") == "live_model":
                _utc(row.get("created_at_utc"))
                if (not re.fullmatch(r"[a-f0-9]{40}", row.get("source_git_sha", ""))
                        or row.get("subject_source") not in ("autonomous", "human")
                        or not row.get("run_id") or not png or not run_raw):
                    raise ValueError("Live artwork has incomplete provenance")
        identity = "|".join((row["task_ref"], str(attempt), digest, row["model_id"], row["journal_tip"]))
        key = _digest(identity.encode())[:20]
        if key in previous:
            if previous[key].get("attempt_receipt_sha256") not in (None, _digest(raw_meta)):
                raise ValueError("Conflicting immutable attempt receipt")
            continue
        rel = "entries/" + key
        live = (row.get("execution_mode") == "live_model" and not fixture
                and row.get("verification_state") == "artifacts_verified")
        descriptor = {
            "schema": SOURCE_SCHEMA, "id": key, "title": row["subject"], "subject": row["subject"],
            "description": row.get("description") or "", "task_ref": row["task_ref"], "attempt": attempt,
            "status": row["status"], "origin": "synthetic_fixture" if fixture else
                "live_model_artifact_verified" if live else "model_generated_unverified",
            "model_id": row["model_id"], "model_digest": row.get("model_digest"),
            "provider_kind": row["provider_kind"], "self_review": row.get("self_review") or {},
            "visual_feedback": row.get("visual_feedback"),
            "external_feedback": row.get("external_feedback"),
            "human_evaluation": row.get("human_evaluation"), "reference_urls": urls,
            "journal_tip": row["journal_tip"], "sha256": digest,
            "source_git_sha": row.get("source_git_sha") or "local-unverified",
            "subject_source": row.get("subject_source", "unverified"),
            "execution_mode": row.get("execution_mode", "synthetic_fixture" if fixture else "unverified"),
            "run_id": row.get("run_id"), "created_at_utc": row.get("created_at_utc"),
            "verification_state": row.get("verification_state", "unverified"),
            "reviewed_at": report["reviewed_at_utc"] if report else None,
            "published_at": datetime.now(timezone.utc).isoformat(), "svg": rel + ".svg",
            "metadata": rel + ".json", "attempt_receipt": rel + ".attempt.json",
            "attempt_receipt_sha256": _digest(raw_meta), "png": rel + ".png" if png else None,
            "png_sha256": _digest(png) if png else None,
            "run_receipt": rel + ".run.json" if run_raw else None,
            "run_receipt_sha256": _digest(run_raw) if run_raw else None,
            "public_review": rel + ".review.json" if report else None,
            "public_review_sha256": _digest(_json_bytes(report)) if report else None,
            "independent_visual_verification": False,
        }
        assets = {key + ".svg": raw, key + ".attempt.json": raw_meta}
        if png:
            assets[key + ".png"] = png
        if run_raw:
            assets[key + ".run.json"] = run_raw
        if report:
            assets[key + ".review.json"] = _json_bytes(report)
        assets[key + ".json"] = _json_bytes(descriptor)
        pending.append((descriptor, assets))
    folder = site / "entries"
    if pending:
        folder.mkdir(parents=True, exist_ok=True)
    for descriptor, assets in pending:
        for filename, data in assets.items():
            dest = folder / filename
            if dest.exists() and dest.read_bytes() != data:
                raise ValueError("Refusing to replace an immutable gallery asset")
            dest.write_bytes(data)
        previous[descriptor["id"]] = descriptor
    listing["entries"] = sorted(previous.values(), key=lambda item: (item["published_at"], item["id"]), reverse=True)
    validate_index(site, listing)
    site.mkdir(parents=True, exist_ok=True)
    output_index.write_bytes(_json_bytes(listing))
    return {"entries": len(listing["entries"]), "added": len(pending), "index": str(output_index), "schema": SCHEMA}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reviewable BEAN Draw gallery")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--review", type=Path, help="Public-safe review manifest bound to exact files")
    args = parser.parse_args()
    print(json.dumps(curate(args.source, args.site, review=args.review), sort_keys=True))


if __name__ == "__main__":
    main()
