#!/usr/bin/env python3
"""Read-only inventory of BEAN Core and Bridge branches, tests and CI signals.

Never executes repository code, dispatches workflows, or writes to GitHub.
Ahead/behind compares Git ancestry, not semantic feature uniqueness.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORIES = ("danieloculus0-bot/BEAN", "danieloculus0-bot/BEAN-AI-Bridge-")
API_ROOT = "https://api.github.com/repos/"
MAX_PAGES = 20


def category(name: str) -> str:
    return name.split("/", 1)[0] if "/" in name else "other"


def summarize_tree(tree: dict) -> dict:
    if tree.get("truncated"):
        raise ValueError("GitHub returned truncated recursive tree")
    paths = sorted(item["path"] for item in tree.get("tree", [])
                   if item.get("type") == "blob" and isinstance(item.get("path"), str))
    tests = [path for path in paths if
             (path.startswith("bean/tests/test_") or path.startswith("tests/test_"))
             and path.endswith(".py")]
    workflows = [path for path in paths
                 if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml"))]
    return {"file_count": len(paths), "test_files": tests,
            "workflow_files": workflows,
            "experiment_files": [p for p in paths if p.startswith("experiments/")]}


def summarize_compare(branch: str, comparison: dict) -> dict:
    changed = [f.get("filename", "") for f in comparison.get("files", [])
               if isinstance(f, dict) and f.get("filename")]
    ahead = comparison.get("ahead_by")
    behind = comparison.get("behind_by")
    return {
        "branch": branch, "group": category(branch),
        "head_status": comparison.get("status"),
        "ahead_by": ahead, "behind_by": behind,
        "comparison_file_count": len(changed),
        "comparison_files": changed,
        "touches_tests": any("/test_" in f or f.startswith("tests/test_") for f in changed),
        "touches_workflows": any(f.startswith(".github/workflows/") for f in changed),
        "classification": (
            "no unique ancestry commits" if ahead == 0 else
            "review diff: unique ancestry commits" if isinstance(ahead, int) and ahead > 0
            else "comparison incomplete"
        ),
        "caution": "A squash-merged or cherry-picked feature can still show as ahead/diverged."
    }


class GitHubReader:
    def __init__(self, token: str | None = None):
        self.token = token

    def get(self, repository: str, path: str):
        if repository not in REPOSITORIES or not path.startswith("/"):
            raise ValueError("unapproved repository or API path")
        url = API_ROOT + repository + path
        headers = {"Accept": "application/vnd.github+json",
                   "User-Agent": "BEAN-read-only-inventory/1.0",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                return json.loads(response.read(8_000_001))
        except HTTPError as exc:
            raise RuntimeError(f"GitHub HTTP {exc.code} for {repository} {path.split('?')[0]}") from None
        except (URLError, OSError, ValueError) as exc:
            raise RuntimeError(f"GitHub request failed for {repository}: {type(exc).__name__}") from exc

    def pages(self, repository: str, endpoint: str) -> list:
        values = []
        for page in range(1, MAX_PAGES + 1):
            separator = "&" if "?" in endpoint else "?"
            batch = self.get(repository, endpoint + separator + f"per_page=100&page={page}")
            if not isinstance(batch, list):
                raise ValueError(f"Unexpected paginated response: {endpoint}")
            values.extend(batch)
            if len(batch) < 100:
                return values
        raise ValueError("Pagination limit reached; inventory is incomplete")


def audit_repository(reader: GitHubReader, repo: str) -> dict:
    main = reader.get(repo, "/branches/main")
    tree = reader.get(repo, "/git/trees/main?recursive=1")
    branches = reader.pages(repo, "/branches")
    prs = reader.pages(repo, "/pulls?state=open")
    result = {
        "repository": repo,
        "main_sha": main["commit"]["sha"],
        "branch_count": len(branches),
        "main_tree": summarize_tree(tree),
        "open_pull_requests": [{
            "number": pr.get("number"), "title": pr.get("title"), "draft": pr.get("draft"),
            "head": (pr.get("head") or {}).get("ref"),
            "base": (pr.get("base") or {}).get("ref"),
            "url": pr.get("html_url")
        } for pr in prs],
        "branches": [], "comparison_errors": [],
    }
    for ref in branches:
        name = ref["name"]
        if name == "main":
            continue
        try:
            head_sha = (ref.get("commit") or {}).get("sha")
            if not head_sha:
                raise ValueError("branch head SHA was missing")
            comparison = reader.get(repo, "/compare/" + result["main_sha"] + "..." + head_sha)
            summary = summarize_compare(name, comparison)
            summary["head_sha"] = head_sha
            result["branches"].append(summary)
        except (RuntimeError, ValueError, KeyError) as exc:
            result["comparison_errors"].append({"branch": name, "error": str(exc)})
    result["branches"].sort(key=lambda x: x["branch"])
    return result


def render_markdown(results: list[dict]) -> str:
    lines = [
        "# BEAN branch and test inventory",
        "",
        "Automatically gathered from GitHub REST, read-only. Ahead/behind is ancestry,",
        "**not** proof that a feature has not already been squash-merged or superseded.",
        "A green CI check verifies its explicit test contract, not general capability.",
        "",
    ]
    for repo in results:
        name = repo["repository"]
        tree = repo["main_tree"]
        lines += [
            f"## {name}",
            "",
            f"- Main commit: `{repo['main_sha']}`",
            f"- Branches discovered including main: {repo['branch_count']}",
            f"- Main Python test modules: {len(tree['test_files'])}",
            f"- Main GitHub workflow files: {len(tree['workflow_files'])}",
            f"- Main experiment files: {len(tree['experiment_files'])}",
            f"- Open pull requests: {len(repo['open_pull_requests'])}",
            f"- Unresolved comparisons: {len(repo['comparison_errors'])}",
            "",
            "### Branch ancestry comparison",
            "",
            "| Branch | Ahead | Behind | Changed files | Test delta | CI delta |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
        for b in repo["branches"]:
            n = b["branch"].replace("|", "\\|")
            lines.append(f"| `{n}` | {b['ahead_by']} | {b['behind_by']} | "
                         f"{b['comparison_file_count']} | "
                         f"{'yes' if b['touches_tests'] else 'no'} | "
                         f"{'yes' if b['touches_workflows'] else 'no'} |")
        if repo["comparison_errors"]:
            lines += ["", "### Comparison failures: inspection required", ""]
            for e in repo["comparison_errors"]:
                lines.append(f"- `{e['branch']}`: {e['error']}")
        lines += ["", "### Test module inventory", ""]
        lines.extend("- `" + p + "`" for p in tree["test_files"])
        lines += ["", "### Workflow inventory", ""]
        lines.extend("- `" + p + "`" for p in tree["workflow_files"])
        lines += ["", "### Open review queue", ""]
        lines.extend(f"- [#{p['number']}: {p['title']}]({p['url']}) "
                     f"(head: `{p['head']}`; draft: {p['draft']})"
                     for p in repo["open_pull_requests"])
        lines += ["", "---", ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="audit-output")
    parser.add_argument("--repo", choices=REPOSITORIES, action="append")
    args = parser.parse_args()
    target = Path(args.output_dir)
    target.mkdir(parents=True, exist_ok=True)
    reader = GitHubReader(os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    results = []
    for repo in args.repo or REPOSITORIES:
        try:
            results.append(audit_repository(reader, repo))
        except (RuntimeError, ValueError, KeyError) as exc:
            results.append({"repository": repo, "fatal_error": str(exc)})
    (target / "inventory.json").write_text(json.dumps(results, indent=2) + "\n",
                                           encoding="utf-8")
    complete = [r for r in results if "fatal_error" not in r]
    (target / "inventory.md").write_text(render_markdown(complete), encoding="utf-8")
    errors = [r for r in results if r.get("fatal_error") or r.get("comparison_errors")]
    for r in results:
        print(r["repository"], "branches:", r.get("branch_count", "ERROR"),
              "test modules:", len(r.get("main_tree", {}).get("test_files", [])),
              "comparison errors:", len(r.get("comparison_errors", [])),
              "fatal:", r.get("fatal_error", "none"))
    if errors:
        print("INCOMPLETE: see inventory.json; never infer missing comparisons passed.")
        return 2
    print("Complete snapshot written; outcomes still require human diff and test review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
