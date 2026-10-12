# BEAN installation and recovery (technical beta)

This repository is BEAN's current **modular Core**, not merely the older "Memory Core 0.1" ZIP layout. The historical `ARCHITECTURE.md` is retained for context. BEAN is an experimental developer beta, **not** an unattended robotics, trading, or multi-tenant deployment.

## Supported developer quickstart

Python 3.10+ on Windows or Linux:

~~~sh
python -m pip install psutil
python -m examples.quickstart_reasoning
python -m examples.capability_proof
python -m bean.runtime.boot_readiness --temp
~~~

These commands exercise fictional/temporary data and an explicit mock reasoning provider. They do **not** demonstrate an internet connection, installed Windows desktop app, trained-general learner or physical actuation. Read [GETTING_STARTED](docs/GETTING_STARTED.md) for context and [README](README.md) for what is on `main` versus isolated experiments.

## Local database backups

From the repository root, after installing its Python dependencies:

~~~sh
python scripts/bean_backup.py --db /path/to/bean_memory.db --backup-dir /safe/backup/location
python scripts/bean_backup.py --verify /safe/backup/location/bean_memory_YYYYMMDDTHHMMSSZ_identifier
~~~

The backup tool now creates a **directory bundle** with the SQLite database, rebuilt audit mirror and integrity manifest. This replaces the original flat `.db` backup naming convention; update any retention scripts before relying on it. Verification includes a disposable SQLite restore-copy drill but does not prove physical power-cut resilience or authenticate the original live mirror. Keep confidential backups protected.

For Windows syntax, recovery steps and limitations, see [Verified backup and release gate](docs/BEAN_BACKUP_RELEASE_GATE_2026-10-12.md).

## Release boundary

GitHub Actions tests the Core across Windows and Ubuntu on Python 3.10/3.12. Experimental neural learners, local MCP integrations and external applications are **not** implicitly production-shipped just because this quickstart works. See [Production readiness audit](docs/PRODUCTION_READINESS_AUDIT_2026-10-11.md).