"""Reusable, read-only BEAN software conformity and integrity audit.

A host supplies pinned project and reference checkouts plus explicit design rules.
Static source checks NEVER establish the behavior of a booted product. BEAN
does not execute tools, authenticate GitHub refs, or grant change authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "bean.software_audit.v1"
KINDS = {"present", "contains_all", "forbids_all", "same_bytes", "git_blob", "runtime_gate"}
MAX_FILE = 8_000_000
MAX_RULES = 100


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def _read(root: Path, relative: str) -> bytes | None:
    if not isinstance(relative, str) or not relative or len(relative) > 400:
        raise ValueError("invalid relative path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError("absolute or traversing paths forbidden")
    base = root.resolve(strict=True)
    candidate = (base / path).resolve(strict=False)
    if not candidate.is_relative_to(base):
        raise ValueError("path escapes audited checkout")
    if not candidate.is_file():
        return None
    if candidate.stat().st_size > MAX_FILE:
        raise ValueError("file exceeds 8 MB read-only audit limit")
    return candidate.read_bytes()


def _rule(root: Path, reference_root: Path | None, rule: dict) -> dict:
    ident = rule["id"]
    path = rule.get("path")
    kind = rule["kind"]
    row = {"id": ident, "requirement": rule["requirement"],
           "source_ref": rule["source_ref"], "kind": kind,
           "path": path, "status": "unverified",
           "evidence": [], "scope": "static_source_only"}
    if kind == "runtime_gate":
        row["scope"] = "requires_live_guest_or_independent_runtime_evidence"
        row["detail"] = "No live behavior is inferred from file presence or a supplied claim"
        return row
    try:
        data = _read(root, path)
        if data is None:
            row["status"], row["detail"] = "fail", "target_missing"
            return row
        row["evidence"] = [{"path": path, "sha256": _digest(data), "bytes": len(data)}]
        if kind == "present":
            matched = True
        elif kind in {"contains_all", "forbids_all"}:
            text = data.decode("utf-8")
            tokens = rule.get("tokens")
            if not isinstance(tokens, list) or not tokens or len(tokens) > 24:
                raise ValueError("1..24 tokens required")
            if not all(isinstance(t, str) and 1 <= len(t) <= 250 for t in tokens):
                raise ValueError("invalid token")
            matches = [t in text for t in tokens]
            matched = all(matches) if kind == "contains_all" else not any(matches)
            row["detail"] = {"checked_tokens": len(tokens),
                             "matching_indices": [i for i, m in enumerate(matches) if m]}
        elif kind == "git_blob":
            expect = rule.get("expected_blob")
            if not isinstance(expect, str) or len(expect) != 40 or any(c not in "0123456789abcdef" for c in expect):
                raise ValueError("expected_blob must be a lowercase full git object SHA")
            row["evidence"][0]["git_blob_sha1"] = _blob_sha(data)
            matched = _blob_sha(data) == expect
        elif kind == "same_bytes":
            if reference_root is None:
                row["detail"] = "reference_checkout_not_supplied"
                return row
            reference_path = rule.get("reference_path")
            reference = _read(reference_root, reference_path)
            if reference is None:
                row["detail"] = "reference_missing"
                return row
            row["evidence"].append({"reference_path": reference_path,
                                    "sha256": _digest(reference), "bytes": len(reference)})
            matched = data == reference
        else:
            raise ValueError("unsupported kind")
        row["status"] = "pass" if matched else "fail"
    except (UnicodeDecodeError, OSError, ValueError) as exc:
        row["status"], row["detail"] = "fail", f"input_error:{type(exc).__name__}"
    return row


def audit_software(root: str | Path, manifest: dict[str, Any], *,
                   reference_root: str | Path | None = None) -> dict:
    """Evaluate bounded input artifacts only; never shell out or fetch URLs."""
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported manifest")
    project = manifest.get("project")
    rules = manifest.get("checks")
    if not isinstance(project, str) or not 1 <= len(project) <= 120:
        raise ValueError("project required")
    if not isinstance(rules, list) or not 1 <= len(rules) <= MAX_RULES:
        raise ValueError("1..100 audit rules required")
    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or not {"id", "requirement", "source_ref", "kind"}.issubset(rule):
            raise ValueError("invalid audit rule schema")
        if rule["kind"] not in KINDS:
            raise ValueError("unsupported rule type")
        ident = rule["id"]
        if not isinstance(ident, str) or not 1 <= len(ident) <= 80 or ident in seen:
            raise ValueError("missing or duplicate rule id")
        seen.add(ident)
        for field in ("requirement", "source_ref"):
            if not isinstance(rule[field], str) or not 1 <= len(rule[field]) <= 400:
                raise ValueError(f"invalid {field}")
        if rule["kind"] != "runtime_gate" and not rule.get("path"):
            raise ValueError("file rule needs a target path")
    root = Path(root)
    reference = Path(reference_root) if reference_root is not None else None
    findings = [_rule(root, reference, item) for item in rules]
    counts = {state: sum(f["status"] == state for f in findings)
              for state in ("pass", "fail", "unverified")}
    verdict = ("FAIL" if counts["fail"] else
               "INCOMPLETE" if counts["unverified"] else "STATIC_SOURCE_PASS")
    report = {
        "schema": SCHEMA, "project": project,
        "baseline_ref": manifest.get("baseline_ref", "not_supplied"),
        "candidate_ref": manifest.get("candidate_ref", "not_supplied"),
        "verdict": verdict, "counts": counts, "findings": findings,
        "source_authentication": "caller_supplied_checkout_not_independently_authenticated",
        "executed_project_code": False, "live_guest_behavior_proven": False,
        "product_release_authorized": False,
    }
    report["receipt_sha256"] = _digest(json.dumps(report, sort_keys=True,
                                                    separators=(",", ":")).encode())
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="BEAN read-only software conformity audit")
    parser.add_argument("--root", required=True, help="Checked-out candidate directory")
    parser.add_argument("--manifest", required=True, help="Explicit source-referenced audit rules")
    parser.add_argument("--reference-root", help="Optional pinned design/baseline checkout")
    parser.add_argument("--output", required=True, help="Report JSON path (outside source checkout preferred)")
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = audit_software(args.root, manifest, reference_root=args.reference_root)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"schema": report["schema"], "project": report["project"],
                      "verdict": report["verdict"], "counts": report["counts"],
                      "receipt_sha256": report["receipt_sha256"]}, sort_keys=True))
    return 2 if report["verdict"] == "FAIL" else 3 if report["verdict"] == "INCOMPLETE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
