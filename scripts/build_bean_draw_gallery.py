#!/usr/bin/env python3
"""Curate public-safe BEAN Draw SVGs from existing Core sketch receipts.

This is a renderer/index builder, not a new memory backend or auto-publisher.
The caller must inspect the drawings and metadata before committing to Pages.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SCHEMA = "bean.draw.gallery.v1"
SOURCE_SCHEMA = "bean.draw.attempt.v1"
ALLOWED_TAGS = {"svg", "g", "defs", "circle", "line", "rect", "polyline"}
ALLOWED_ATTRS = {
    "width", "height", "viewBox", "version", "x", "y", "x1", "y1",
    "x2", "y2", "cx", "cy", "r", "points", "stroke", "stroke-width",
    "stroke-linecap", "stroke-linejoin", "fill", "fill-opacity", "opacity",
    "transform", "id",
}
MAX_SVG_BYTES = 250000


def validate_svg(raw: bytes) -> None:
    """Reject scripting, references, unsupported elements and oversized art."""
    if not raw or len(raw) > MAX_SVG_BYTES:
        raise ValueError("SVG is empty or oversized")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("SVG is not well-formed XML") from exc
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("Not an SVG document")
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ALLOWED_TAGS:
            raise ValueError("Unapproved SVG element: " + tag)
        if el.text and el.text.strip():
            raise ValueError("Embedded SVG text is not allowed")
        if len(el.attrib) > 24:
            raise ValueError("Excessive SVG attributes")
        for key, value in el.attrib.items():
            if key not in ALLOWED_ATTRS or len(value) > 2000:
                raise ValueError("Unapproved SVG attribute: " + key)
            if "url(" in value.lower() or "javascript:" in value.lower():
                raise ValueError("External SVG reference not allowed")


def curate(source: Path, site: Path) -> dict:
    source = Path(source)
    site = Path(site)
    metas = sorted(source.glob("attempt_[0-9][0-9].json"))
    if not metas:
        raise ValueError("No BEAN sketch attempt sidecars found")
    output_index = site / "index.json"
    if output_index.exists():
        listing = json.loads(output_index.read_text(encoding="utf-8"))
        if listing.get("schema") != SCHEMA or not isinstance(listing.get("entries"), list):
            raise ValueError("Existing gallery index has an unknown schema")
    else:
        listing = {"schema": SCHEMA, "entries": []}
    previous = {item["id"]: item for item in listing["entries"]}
    inserted = 0
    for metadata in metas:
        row = json.loads(metadata.read_text(encoding="utf-8"))
        if row.get("schema") != SOURCE_SCHEMA:
            raise ValueError("Unknown drawing receipt schema")
        attempt = row.get("attempt")
        if type(attempt) is not int or not 1 <= attempt <= 99:
            raise ValueError("Invalid attempt")
        expected_name = "attempt_%02d.svg" % attempt
        if row.get("svg_file") is None:
            continue  # Failure receipt, no picture to curate
        if row["svg_file"] != expected_name:
            raise ValueError("Unsafe or inconsistent drawing filename")
        source_svg = source / expected_name
        if not source_svg.is_file():
            raise ValueError("Drawing referenced by receipt does not exist")
        raw = source_svg.read_bytes()
        validate_svg(raw)
        digest = sha256(raw).hexdigest()
        if row.get("svg_sha256") != digest:
            raise ValueError("Drawing no longer matches BEAN's journal receipt")
        for key in ("task_ref", "subject", "status", "model_id", "provider_kind",
                    "journal_tip"):
            if not isinstance(row.get(key), str) or not 0 < len(row[key]) <= 300:
                raise ValueError("Missing or unbounded drawing provenance: " + key)
        reference_urls = row.get("reference_urls", [])
        if not isinstance(reference_urls, list) or len(reference_urls) > 12:
            raise ValueError("Invalid reference URL list")
        for url in reference_urls:
            if not isinstance(url, str) or len(url) > 600 or not re.match(r"^https://", url):
                raise ValueError("Unapproved reference URL")
        identity = "|".join((row["task_ref"], str(attempt), digest,
                             row["model_id"], row["journal_tip"]))
        key = sha256(identity.encode("utf-8")).hexdigest()[:20]
        rel_svg = "entries/" + key + ".svg"
        rel_meta = "entries/" + key + ".json"
        if key in previous:
            if previous[key].get("sha256") != digest:
                raise ValueError("Conflicting gallery identity")
            continue
        folder = site / "entries"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (key + ".svg")).write_bytes(raw)
        source_kind = ("synthetic_fixture" if row["provider_kind"] == "synthetic_fixture"
                       else "model_generated_unverified")
        descriptor = {
            "schema": SOURCE_SCHEMA,
            "id": key,
            "title": row["subject"],
            "subject": row["subject"],
            "description": row.get("description") or "",
            "task_ref": row["task_ref"],
            "attempt": attempt,
            "status": row["status"],
            "origin": source_kind,
            "model_id": row["model_id"],
            "provider_kind": row["provider_kind"],
            "self_review": row.get("self_review") or {},
            "visual_feedback": row.get("visual_feedback"),
            "reference_urls": reference_urls,
            "journal_tip": row["journal_tip"],
            "sha256": digest,
            "source_git_sha": row.get("source_git_sha") or "local-unverified",
            "reviewed_at": None,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "svg": rel_svg,
            "metadata": rel_meta,
            "independent_visual_verification": False,
        }
        (folder / (key + ".json")).write_text(
            json.dumps(descriptor, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8")
        previous[key] = descriptor
        inserted += 1
    site.mkdir(parents=True, exist_ok=True)
    listing["entries"] = sorted(
        previous.values(),
        key=lambda item: (item["published_at"], item["id"]), reverse=True)
    output_index.write_text(json.dumps(
        listing, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return {"entries": len(listing["entries"]), "added": inserted,
            "index": str(output_index), "schema": SCHEMA}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reviewable BEAN Draw gallery")
    parser.add_argument("--source", type=Path, required=True,
                        help="Folder containing attempt_01.svg and attempt_01.json")
    parser.add_argument("--site", type=Path, required=True,
                        help="Output GitHub Pages docs/bean-draw folder or CI staging dir")
    args = parser.parse_args()
    print(json.dumps(curate(args.source, args.site), sort_keys=True))


if __name__ == "__main__":
    main()
