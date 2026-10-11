# BEAN Lab 011 — durable task behaviors

**Experimental, opt-in, local-only.** Building on BEAN's existing tick scheduler and report Watcher, this module adds a persistent SQLite task ledger and strictly named built-in actions. It does not install a cloud worker, turn on live trades, execute shell commands, or authorize physical movement.

## Why it exists
A runtime tick is not a durable task. BEAN needs to tell the difference between **task assigned**, **due**, **attempted**, **verified**, **failed**, **not available**, and **outcome unknown after a restart**. A repeated task should never manufacture success when information is absent. A crash between performing a side effect and committing a result must not cause silent execution again.

## Current safe action allowlist

| Action | Behavior | Output |
|---|---|---|
| \`integrity_check\` | Run SQLite quick_check | Verified or N/A/error |
| \`watch_reports\` | Force-read configured local normalized reports using the existing BEAN Watcher | Verified, partial, or N/A |
| \`inner_weather\` | Update machine-native attention/resource pressure snapshot | Recorded result |
| \`relationship_review\` | Inspect recent recorded relationship events and recompute bounded summaries | Recorded result |

These are **BEAN-native behaviors only**, not outbound actions. No arbitrary command, dynamic import, trade, email, hardware control, or self-updating executable is accepted from a task configuration.

## Enable with a trusted local file

Create a JSON file controlled by the system administrator (not readable or writable by arbitrary network users):

\`\`\`json
{
  "tasks": [
    {"task_id": "bean_health", "action": "integrity_check", "interval_seconds": 3600},
    {"task_id": "bean_reports", "action": "watch_reports", "interval_seconds": 300},
    {"task_id": "bean_relationships", "action": "relationship_review", "interval_seconds": 86400},
    {"task_id": "bean_inner_weather", "action": "inner_weather", "interval_seconds": 900}
  ]
}
\`\`\`

\`BEAN_TASK_CONFIG=/path/to/approved/task-config.json python bean_run.py --ticks 120\`

Without \`BEAN_TASK_CONFIG\`, there is **no durable-task poller or additional task execution**. Existing legacy tick activities run as they did before.

On startup the task engine reuses the existing BEAN SQLite memory file, scans for interrupted tasks, marks their outcome **unknown**, and requires independent human review. It then reconciles the approved local config. Removing a task from the config pauses it. Changing an existing action requires creating a new task identity.

## Invariants

1. The allowlist comes from trusted application code, not an LLM request or a user-provided name that resolves arbitrary Python.
2. SQLite stores task definitions, due times, attempts, and each execution attempt, across sessions.
3. Failed known outcomes retry with bounded backoff and stop after a maximum attempt count.
4. An interrupted **running** task is marked \`unknown\` and \`needs_review\`; BEAN will **not** automatically replay it even if the config still lists it.
5. Missing report data is **N/A**, never zero or proof of success. Report provenance still comes from the Watcher.
6. The scheduler does not execute past-due work repeatedly in a catch-up storm after downtime.
7. Readable history is inspectable through the DB/API. The module does **not** register task-creation commands on the untrusted file inbox.
8. No sensitive details from the builder's life are included, and the scheduler does not infer authority from affection, trust, or roleplay.
9. The optional event log is supplemental: the SQLite durable task-run record remains authoritative.
10. Human review is required to determine whether an interrupted action truly occurred. This prototype has no operator review UI yet.

## Validation

\`python -m pytest bean/tests/test_task_engine_lab011.py -q\`

\`python -m pytest bean/tests -q\`

GitHub Actions tests the complete regression suite on Windows and Linux with Python 3.10 and 3.12. Tests are synthetic; they demonstrate scheduling rules and database persistence, not live 24/7 cloud uptime, backup durability, OS service recovery, or permissioned network integration.

## Production gates

- Implement a separately authenticated administrative review/resume flow, never trusting a claimed role in a JSON payload.
- Make immutable config revisions and signed, independent execution receipts.
- Establish durable memory backups, off-site restore drills, and task migration/versioning.
- Integrate systemd or Windows Service hosting and an external heartbeat before claiming unattended operation.
- Add external effectors only through narrow capability-specific authorization and per-operation safety checks, including separate policies for trading and robots.
