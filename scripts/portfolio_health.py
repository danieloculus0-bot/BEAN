#!/usr/bin/env python3
"""Inventory public GitHub repositories and exact-main-head CI without claiming release readiness.

This is a read-only GitHub evidence collector. It does not execute product tests,
access private repositories, or make judgments about product quality.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

API = "https://api.github.com"
BAD = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}
PENDING = {"queued", "in_progress", "pending", "requested", "waiting"}


def github_get(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BEAN-public-portfolio-evidence",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(API + path, headers=headers), timeout=25) as response:
        return json.load(response)


def summarize_checks(checks):
    """Report exactly what GitHub says; missing checks are unknown, not passing."""
    if not checks:
        return {"status": "unknown", "passed": 0, "failed": 0, "pending": 0, "other": 0}
    passed = sum(c.get("conclusion") == "success" for c in checks)
    failed = sum(c.get("conclusion") in BAD for c in checks)
    pending = sum(c.get("status") != "completed" or c.get("status") in PENDING for c in checks)
    other = len(checks) - passed - failed - pending
    status = "failed" if failed else "pending" if pending else "passed" if passed else "unknown"
    return {"status": status, "passed": passed, "failed": failed, "pending": pending, "other": other}


def collect(owner: str, request=github_get):
    """Collect live public inventory and main-head checks. Preserve partial failures."""
    repos = []
    page = 1
    while True:
        batch = request(f"/users/{quote(owner)}/repos?type=owner&per_page=100&page={page}")
        repos.extend(x for x in batch if x.get("owner", {}).get("login", "").lower() == owner.lower())
        if len(batch) < 100:
            break
        page += 1
    results = []
    for entry in sorted(repos, key=lambda r: r["name"].lower()):
        name = entry["name"]
        branch = entry["default_branch"]
        root = f"/repos/{quote(owner)}/{quote(name)}"
        row = {
            "name": name, "url": entry["html_url"], "branch": branch,
            "archived": bool(entry.get("archived", False)),
            "head_sha": None, "ci": summarize_checks([]), "open_prs": None,
            "errors": [],
        }
        try:
            ref = request(root + "/branches/" + quote(branch, safe=""))
            sha = ref["commit"]["sha"]
            row["head_sha"] = sha
            checks = request(root + "/commits/" + sha + "/check-runs?per_page=100")
            row["ci"] = summarize_checks(checks.get("check_runs", []))
            if checks.get("total_count", 0) > len(checks.get("check_runs", [])):
                row["errors"].append("CI has more than 100 checks; status is incomplete")
                row["ci"]["status"] = "incomplete"
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            row["errors"].append(f"CI metadata unavailable: {type(error).__name__}")
        try:
            prs = request(root + "/pulls?state=open&per_page=100")
            row["open_prs"] = str(len(prs)) if len(prs) < 100 else "100+"
        except (ValueError, OSError, RuntimeError) as error:
            row["errors"].append(f"PR metadata unavailable: {type(error).__name__}")
        results.append(row)
    return {
        "schema_version": 1, "owner": owner,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "public repositories, default-branch HEAD, GitHub check runs and open PRs",
        "repos": results,
    }


def markdown(report):
    lines = [
        "# Public GitHub portfolio health",
        "",
        f"Generated UTC: {report['generated_at_utc']}",
        "",
        "This is an inventory of GitHub evidence, not a release certification. "
        "A passing check does not prove full runtime functionality.",
        "",
        "| Repository | Default HEAD | Exact-head checks | Open PRs | Notes |",
        "|---|---|---|---|---|",
    ]
    for r in report["repos"]:
        ci = r["ci"]
        summary = f"{ci['status']} ({ci['passed']} pass, {ci['failed']} fail, {ci['pending']} pending)"
        notes = "; ".join(r["errors"]) or ("archived" if r["archived"] else "")
        lines.append(
            f"| [{r['name']}]({r['url']}) | "
            f"{(r['head_sha'] or 'unknown')[:12]} | {summary} | "
            f"{r['open_prs'] if r['open_prs'] is not None else 'unknown'} | {notes} |"
        )
    lines += ["", f"Total public repositories: {len(report['repos'])}", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="danieloculus0-bot")
    parser.add_argument("--out", type=Path, default=Path("portfolio-health"))
    args = parser.parse_args()
    try:
        report = collect(args.owner)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Portfolio inventory unavailable: {type(error).__name__}: {error}\n")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "portfolio_health.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.out / "portfolio_health.md").write_text(markdown(report), encoding="utf-8")
    print(f"Collected {len(report['repos'])} public repositories in {args.out}")


if __name__ == "__main__":
    main()
