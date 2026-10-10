# Native BEAN Watcher: recall, working memory and evidence

BEAN's primary source is `bean/runtime/watcher.py`; it is not a copy of
the separate ERP Bridge. Watcher plugs into `bean_run.py`, the same BEAN
tick scheduler, SQLite/JSONL event logger and Python compiler/test workflow.

## Principle

- RAM holds current source state, last verified results, recent transition
  hashes and independent monotonic recall timers.
- The local BEAN SQLite ledger records changes with
  `event_type=observation`, `subtype=watcher_transition`; BEAN can
  reconstruct prior verified evidence after a restart.
- A restarted watcher marks old readings N/A until the actual source is read
  again. Earlier values remain visible *only* as last verified history.
- `recall_frequency` controls the **interval between checks**, in seconds.
  Each report has its own recall and `stale_after` threshold.
- On a changed JSON report file, the next BEAN runtime tick checks early;
  adapters can also explicitly `watcher.ingest(key, ReportEvidence(...))`.
- Missing source, incomplete export, missing required metric, no evidence,
  unsupported field value, or unavailable source means **N/A**.
  Zero is valid only from an explicit complete and evidenced report.
- Stale data shows N/A for the current value while preserving historical
  evidence. No probability/confidence score is manufactured.
- In-memory status is readable from `ctx["watcher"].snapshot()` or existing
  inbox commands `watcher_status` / `watcher_recheck`. No unapproved
  network endpoint or credentials are created.

## Opt-in runtime configuration

Both variables are required to enable Watcher; otherwise BEAN behaves as before.

```sh
export BEAN_WATCH_CONFIG=/home/bean/bean_data/watch/config.json
export BEAN_WATCH_REPORT_DIR=/home/bean/bean_data/watch/reports
python3 bean_run.py --ticks 10
```

Example `config.json` (fake identifiers only):

```json
{
  "reports": [
    {
      "key": "rma",
      "fields": ["rma_count", "rma_quantity", "rma_cost"],
      "recall_frequency": 60,
      "stale_after": 900
    },
    {
      "key": "shipping",
      "fields": ["completed_jobs", "on_time_jobs"],
      "recall_frequency": 120,
      "stale_after": 1800
    }
  ]
}
```

A read-only source adapter deposits `reports/rma.json`:

```json
{
  "report_id": "synthetic-rma-2026-10-10",
  "observed_at": "2026-10-10T08:00:00+00:00",
  "complete": true,
  "values": {
    "rma_count": 0,
    "rma_quantity": 0,
    "rma_cost": 0
  },
  "evidence_ids": ["test-fixture-sha256:example"]
}
```

**Do not** set `complete: true` simply because an export succeeded.
The ERP adapter must verify the expected reporting scope, period, and source
coverage before asserting completeness. A file with missing rows is not
proof of zero events. A snapshot can include extra source fields without
being used by Watcher.

## Production boundaries

Only local JSON output files are read, with no live ERP connection.
A trusted external exporter is responsible for authorization, reconciliation,
atomic report publication, valid source timestamps, provenance/evidence IDs,
and marking source completeness. Configure reports outside the Git checkout.
The SQLite and JSONL event trail can contain metric values and must remain
under local access controls. Deployers should not publish company reports
or evidence files to public GitHub.

This module is not a continuous background cloud service. It works when
BEAN's own runtime is running; the existing tick loop drives polling.

## Regression tests

```bash
python -m compileall -q bean bean_run.py
python -m pytest bean/tests/test_watcher.py -q
bash scripts/run_brain_smoke_tests.sh
```

The GitHub CI checks Python 3.10 and 3.12 on Linux and Windows.
