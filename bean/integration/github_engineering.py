"""BEAN GitHub Engineering Bridge: read-only remote discovery with durable receipts.

The bridge reads public or authorized repository metadata, catalogs branch/PR/CI
signals and records changes in BEAN's local SQLite database. It neither runs
GitHub code nor executes workflow dispatches, merges, shell commands or pushes.
Team roles are suggestions, not claims that other agents have been contacted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS github_engineering_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repository TEXT NOT NULL,
  kind TEXT NOT NULL,
  external_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  entry_hash TEXT NOT NULL,
  observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bean_gh_subject
  ON github_engineering_events(repository, kind, external_id, id);
CREATE TABLE IF NOT EXISTS github_engineering_syncs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repository TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  branches_seen INTEGER NOT NULL,
  prs_seen INTEGER NOT NULL,
  runs_seen INTEGER NOT NULL,
  new_events INTEGER NOT NULL
);
"""


def _canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text(value, limit=260) -> str:
    return str(value or "")[:limit]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class GitHubReadClient:
    """GitHub REST reader. Accepts token through memory/environment only."""

    def __init__(self, repository: str, token: str | None = None, fetch_json=None):
        if not _REPO.fullmatch(repository) or ".." in repository.split("/"):
            raise ValueError("repository must be owner/name")
        self.repository = repository
        self._token = token if token is not None else (
            os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        )
        self._fetch_json = fetch_json

    def get(self, endpoint: str):
        if endpoint not in {
            "/branches?per_page=100",
            "/pulls?state=open&per_page=100",
            "/actions/runs?per_page=50",
        }:
            raise ValueError("unsupported GitHub read endpoint")
        if self._fetch_json is not None:
            return self._fetch_json(endpoint)
        req = Request(
            "https://api.github.com/repos/" + self.repository + endpoint,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "BEAN-engineering-bridge/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": "Bearer " + self._token} if self._token else {}),
            },
        )
        try:
            with urlopen(req, timeout=25) as response:
                content = response.read(2_000_001)
        except HTTPError as exc:
            raise RuntimeError(
                "GitHub read returned HTTP " + str(exc.code)
                + "; confirm repository access or API limits"
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("GitHub unavailable: " + type(exc).__name__) from None
        if len(content) > 2_000_000:
            raise RuntimeError("GitHub response exceeded size limit")
        try:
            return json.loads(content)
        except ValueError as exc:
            raise RuntimeError("GitHub returned malformed JSON") from exc

    def snapshot(self) -> dict:
        """Gather bounded, normalized remote metadata before any DB write."""
        branches = self.get("/branches?per_page=100")
        prs = self.get("/pulls?state=open&per_page=100")
        runs_data = self.get("/actions/runs?per_page=50")
        if not isinstance(branches, list) or not isinstance(prs, list):
            raise ValueError("GitHub returned an unexpected branches/PRs shape")
        if not isinstance(runs_data, dict) or not isinstance(runs_data.get("workflow_runs"), list):
            raise ValueError("GitHub returned an unexpected workflow runs shape")
        runs = runs_data["workflow_runs"]
        records = []
        for b in branches[:100]:
            if isinstance(b, dict) and b.get("name"):
                records.append(("branch", _text(b["name"], 160), {
                    "name": _text(b["name"], 160),
                    "sha": _text((b.get("commit") or {}).get("sha"), 64),
                    "protected": bool(b.get("protected", False)),
                }))
        for p in prs[:100]:
            if isinstance(p, dict) and isinstance(p.get("number"), int):
                records.append(("pull_request", str(p["number"]), {
                    "number": p["number"],
                    "title": _text(p.get("title")),
                    "url": _text(p.get("html_url"), 400),
                    "head": _text((p.get("head") or {}).get("ref"), 160),
                    "head_sha": _text((p.get("head") or {}).get("sha"), 64),
                    "base": _text((p.get("base") or {}).get("ref"), 160),
                    "draft": bool(p.get("draft")),
                    "state": _text(p.get("state"), 25),
                    "updated_at": _text(p.get("updated_at"), 40),
                }))
        for w in runs[:50]:
            if isinstance(w, dict) and isinstance(w.get("id"), int):
                pr_numbers = [
                    item["number"]
                    for item in (w.get("pull_requests") or [])[:20]
                    if isinstance(item, dict) and isinstance(item.get("number"), int)
                ]
                records.append(("workflow_run", str(w["id"]), {
                    "id": w["id"],
                    "name": _text(w.get("name"), 180),
                    "head_branch": _text(w.get("head_branch"), 160),
                    "head_sha": _text(w.get("head_sha"), 64),
                    "status": _text(w.get("status"), 50),
                    "conclusion": _text(w.get("conclusion"), 50),
                    "url": _text(w.get("html_url"), 400),
                    "prs": pr_numbers,
                    "updated_at": _text(w.get("updated_at"), 40),
                }))
        return {
            "repository": self.repository,
            "records": records,
            "counts": {"branches": len(branches), "pull_requests": len(prs),
                       "workflow_runs": len(runs)},
            "may_be_paginated": {"branches": len(branches) >= 100,
                                 "pull_requests": len(prs) >= 100,
                                 "workflow_runs": len(runs) >= 50},
        }


class EngineeringJournal:
    """Append-only change history with hash-chain verification on every sync."""

    def __init__(self, db_path: str | Path):
        target = Path(db_path)
        if target.is_symlink():
            raise ValueError("refusing a symlinked BEAN journal")
        if not target.parent.is_dir():
            raise ValueError("journal directory must already exist")
        self.conn = sqlite3.connect(str(target))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self.verify()

    def verify(self) -> None:
        previous = "GENESIS"
        rows = self.conn.execute(
            "SELECT repository,kind,external_id,payload_json,fingerprint,"
            "previous_hash,entry_hash,observed_at FROM github_engineering_events "
            "ORDER BY id"
        )
        for row in rows:
            payload = json.loads(row["payload_json"])
            if row["fingerprint"] != _hash(_canonical(payload)):
                raise ValueError("BEAN GitHub receipt content was modified")
            envelope = {
                "repo": row["repository"], "kind": row["kind"],
                "id": row["external_id"], "fingerprint": row["fingerprint"],
                "previous": previous, "observed_at": row["observed_at"],
            }
            if (row["previous_hash"] != previous
                    or row["entry_hash"] != _hash(_canonical(envelope))):
                raise ValueError("BEAN GitHub receipt chain failed verification")
            previous = row["entry_hash"]

    def ingest(self, snapshot: dict) -> dict:
        self.verify()
        if not isinstance(snapshot.get("records"), list):
            raise ValueError("invalid GitHub snapshot")
        repo = snapshot["repository"]
        if not isinstance(repo, str) or not _REPO.fullmatch(repo):
            raise ValueError("invalid repository")
        clock = _utc()
        inserted = 0
        with self.conn:
            tail = self.conn.execute(
                "SELECT entry_hash FROM github_engineering_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            previous = tail["entry_hash"] if tail else "GENESIS"
            for kind, external_id, payload in snapshot["records"]:
                if kind not in {"branch", "pull_request", "workflow_run"}:
                    raise ValueError("invalid GitHub record kind")
                fingerprint = _hash(_canonical(payload))
                row = self.conn.execute(
                    "SELECT fingerprint FROM github_engineering_events "
                    "WHERE repository=? AND kind=? AND external_id=? ORDER BY id DESC LIMIT 1",
                    (repo, kind, external_id),
                ).fetchone()
                if row and row["fingerprint"] == fingerprint:
                    continue
                envelope = {
                    "repo": repo, "kind": kind, "id": external_id,
                    "fingerprint": fingerprint, "previous": previous,
                    "observed_at": clock,
                }
                entry = _hash(_canonical(envelope))
                self.conn.execute(
                    "INSERT INTO github_engineering_events "
                    "(repository,kind,external_id,payload_json,fingerprint,previous_hash,"
                    "entry_hash,observed_at) VALUES (?,?,?,?,?,?,?,?)",
                    (repo, kind, external_id, _canonical(payload).decode("utf-8"),
                     fingerprint, previous, entry, clock),
                )
                previous = entry
                inserted += 1
            count = snapshot["counts"]
            self.conn.execute(
                "INSERT INTO github_engineering_syncs "
                "(repository,observed_at,branches_seen,prs_seen,runs_seen,new_events)"
                " VALUES (?,?,?,?,?,?)",
                (repo, clock, count["branches"], count["pull_requests"],
                 count["workflow_runs"], inserted),
            )
        self.verify()
        return {"new_events": inserted, "observed_at": clock, "counts": count,
                "may_be_paginated": snapshot["may_be_paginated"]}

    def review_queue(self, repository: str, *, max_items: int = 12) -> list[dict]:
        """Evidence-backed work queue; never invent failures or agent assignments."""
        if not _REPO.fullmatch(repository):
            raise ValueError("invalid repository")
        rows = self.conn.execute(
            "SELECT kind,external_id,payload_json FROM github_engineering_events "
            "WHERE repository=? ORDER BY id DESC",
            (repository,),
        )
        latest = {}
        for row in rows:
            key = (row["kind"], row["external_id"])
            if key not in latest:
                latest[key] = json.loads(row["payload_json"])
        failures = [
            value for (kind, _), value in latest.items()
            if kind == "workflow_run" and value.get("conclusion") in
            {"failure", "timed_out", "cancelled", "action_required"}
        ]
        queue = []
        for run in sorted(failures, key=lambda r: (r.get("updated_at") or ""), reverse=True):
            queue.append({
                "priority": "investigate",
                "subject": "workflow_run",
                "name": run["name"],
                "url": run["url"],
                "conclusion": run["conclusion"],
                "related_pull_requests": run["prs"],
                "next_role": "reviewer",
                "recommendation": "Inspect CI failure evidence before proposing a repair",
            })
            if len(queue) >= max_items:
                return queue
        prs = [
            value for (kind, _), value in latest.items()
            if kind == "pull_request" and value.get("state") == "open"
        ]
        for pr in sorted(prs, key=lambda r: (r.get("updated_at") or ""), reverse=True):
            queue.append({
                "priority": "review",
                "subject": "pull_request",
                "name": pr["title"],
                "url": pr["url"],
                "draft": pr["draft"],
                "next_role": "tester",
                "recommendation": "Review the proposed branch and linked CI before any changes",
            })
            if len(queue) >= max_items:
                break
        return queue

    def close(self):
        self.conn.close()


def run_bridge(repository: str, db_path: str | Path, *, fetch_json=None) -> dict:
    """One bounded discovery pass; stores evidence, not executive authority."""
    snapshot = GitHubReadClient(repository, fetch_json=fetch_json).snapshot()
    journal = EngineeringJournal(db_path)
    try:
        ingestion = journal.ingest(snapshot)
        return {
            "schema": "bean.github.engineering.v0.1",
            "repository": repository,
            "db_path": str(db_path),
            "mode": "read_only",
            **ingestion,
            "work_queue": journal.review_queue(repository),
        }
    finally:
        journal.close()


def main():
    p = argparse.ArgumentParser(description="BEAN GitHub engineering discovery")
    p.add_argument("--repo", default="danieloculus0-bot/BEAN")
    p.add_argument("--db", default=os.environ.get("BEAN_DB_PATH"))
    args = p.parse_args()
    if not args.db:
        p.error("Specify --db or set BEAN_DB_PATH")
    result = run_bridge(args.repo, args.db)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
