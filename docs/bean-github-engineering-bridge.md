# BEAN GitHub Engineering Bridge (research v0.1)

BEAN's Windows core can now **read current GitHub branch, pull request and
GitHub Actions results into a durable local SQLite engineering journal**.
The bridge records and verifies a hash chain of source receipts, avoids
re-recording unchanged observations, and highlights failed CI runs and open
engineering reviews. Unlike CI artifacts, this journal lives on the BEAN PC
and persists between restarts.

## Windows one-time use

From `D:\BEAN\core` after checking out the engineering-bridge branch:

```powershell
& 'D:\BEAN\.venv\Scripts\python.exe' -m bean.integration.github_engineering --repo danieloculus0-bot/BEAN --db 'D:\BEAN\data\bean_memory.db'
```

The destination can also come from `BEAN_DB_PATH`; the bridge creates
`github_engineering_events` and `github_engineering_syncs` tables in that
database without replacing BEAN's identity/session/reasoning tables.

Public repository reads work without GitHub authentication, subject to the
GitHub API's limits. For private repositories or higher limits, inject a
read-only scoped GitHub App/token via `GH_TOKEN` or `GITHUB_TOKEN`.
Do **not** paste keys in shell commands or commit keys. The bridge does not
serialize access tokens into its database, print them, or write them to disk.

## What a real sync does

1. Read up to the first 100 branch references, first 100 open PRs, and first
   50 recent workflow runs from GitHub's official REST API.
2. Normalize branch hashes, PR titles and URLs, CI status and linked PRs.
3. Append hash-chained receipts **only when that subject's observable state
   changes**; verify the full journal chain before and after adding events.
4. Print a small evidence-backed queue prioritizing failing CI runs, followed
   by open PRs. The labels `reviewer` and `tester` are **suggested jobs**,
   not contacted humans or active separate AI agents.
5. Repeated runs reuse history. Errors or unexpected remote responses stop
   without falsely marking jobs as passed.

**Pagination**: v0.1 explicitly reports when GitHub might have additional
pages; do not treat a cap-limited snapshot as an exhaustive repository audit.

**Security**: GitHub data (including PR titles/descriptions) is untrusted
evidence. The bridge does not run checkout commands, model-generated code,
workflows, merges, new branches or writes to GitHub. The engineering journal
is separate from the Lab019 candidate history. API transport is read only.
The SQLite SHA chain detects changes to history but does not provide
cryptographic authentication against attackers who can rewrite the entire
database.

## Next engineering milestones

- Join read-only PR/CI receipts with BEAN's local Lab019/Lab023 candidate and
  holdout histories to classify verified outcomes.
- Give dedicated role workers (builder, reviewer, falsifier, tester) explicitly
  recorded assignments, inputs, immutable test results and source references.
- Add GitHub Actions test dispatch only through a separately authorized GitHub
  App with restricted `actions:write` scope and known trusted workflows.
- Promote independently tested patches to review branches with CI receipts.
  No automatic main merges or arbitrary Windows host execution in v0.1.

Run offline tests:

```powershell
& 'D:\BEAN\.venv\Scripts\python.exe' -m pytest bean/tests/test_github_engineering_bridge.py -q
```
