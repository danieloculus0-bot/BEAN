# BEAN verified memory backup and release-completeness gate

**Review date:** October 12, 2026. **Scope:** BEAN Core Main's local SQLite memory and developer-beta release. This is a source/CI review, not a power-cut test, field deployment, or external security audit.

## Why this fortification was needed

The previous \`scripts/bean_backup.py\` used SQLite's online backup API, but immediately announced success without a destination integrity check, full restore exercise, source/audit history receipt, duplicate-name protection, or partial-publication guard. A database file existing on disk did not prove it could be restored.

The updated command creates a **complete immutable-by-convention directory bundle**:

- \`memory.db\`: consistent SQLite snapshot made using the online backup API, including committed WAL changes in the backup snapshot
- \`memory.db.events.jsonl\`: canonical audit history regenerated from the **same backup snapshot**, not copied from a concurrently changing sidecar
- \`manifest.json\`: SHA256 of both files, event count and final event ID, hash of canonical event stream, and a whole-database logical export hash

Before publication, the tool checks SQLite \`PRAGMA quick_check\` and \`foreign_key_check\`, compares canonical audit bytes to the mirror, backs the snapshot up into a **new disposable SQLite database**, reruns checks and compares the **entire schema/data logical hash**. It creates the bundle in a private staging directory and publishes by renaming the fully verified directory. Randomized paths prevent same-second collisions. On error, the partial staging directory is removed and no success line is printed.

**Important:** \`verify_backup\` verifies self-consistency, not authenticated external truth. The manifest is not signed. The *live source's* independent JSONL is **not** verified or preserved by this tool, and existing source-sidecar tampering can remain undetected. Restoring SQLite's canonical event history from a backup does not prove that the original mirror was untampered. Retain an independent archival copy of source logs if investigating tampering. Confidential records in bundles require restricted filesystem access, encryption and separate off-host copies.

## Operator commands

The existing environment variables still apply: \`BEAN_DB_PATH\`, \`BEAN_BACKUP_DIR\`. The default source database remains \`/home/bean/bean_data/bean_memory.db\`.

~~~bash
python scripts/bean_backup.py --db /path/to/bean_memory.db --backup-dir /secure/backups
python scripts/bean_backup.py --verify /secure/backups/bean_memory_YYYYMMDDTHHMMSSZ_identifier
~~~

On Windows PowerShell:

~~~powershell
python scripts/bean_backup.py --db "D:\BEAN\data\bean_memory.db" --backup-dir "D:\BEAN\backups"
python scripts/bean_backup.py --verify "D:\BEAN\backups\bean_memory_YYYYMMDDTHHMMSSZ_identifier"
~~~

The first command writes and verifies a new directory. The second returns status \`verified\` and \`restore_drill: passed\` **only** when the files still match and a disposable restore succeeds. Both return nonzero on failure. Neither overwrites a live BEAN database.

**Upgrade compatibility:** Old backups were individual \`bean_memory_TIMESTAMP.db\` files. New backups are directories containing the three files. Operators must update any rotation scripts, retention jobs, copying rules and restore runbooks which assumed a flat \`.db\` filename. Old backups are **not** retroactively certified by the new verifier. Do not remove the originals during migration.

## Recovery procedure, with explicit approval

1. Stop any process that writes to the affected BEAN database and preserve the original files for investigation.
2. Run \`--verify\` against the intended bundle, including the disposable restore drill.
3. On a **separate recovery machine or directory**, copy \`memory.db\` to the chosen recovery path, and copy \`memory.db.events.jsonl\` to \`<chosen-database-path>.events.jsonl\`. Preserve source timestamps, permissions and original incident evidence as required.
4. Run the normal BEAN startup/boot-readiness checks **against the recovery copy**, validate expected recent sessions/records, and only then choose whether to switch a live deployment. Do not claim zero lost events; evaluate the manifest event count and last event ID against available incident evidence.
5. Never make a restore by overwriting the running database, and never merge a restored journal with a newer live journal automatically.

## CI acceptance and remaining limits

\`bean/tests/test_verified_backup.py\` creates real disposable Core databases and exercises live WAL backup, mirror alignment, SQLite restore, duplicate-second output, corrupt/missing sources, changed mirror/database and CLI verification. \`.github/workflows/brain-smoke.yml\` exercises this suite on Windows and Ubuntu, Python 3.10 and 3.12.

**Still not certified:** unclean power-loss durability; disk-full/OS permission fault injection; >=24-hour write/restore stress; migration to/from older schemas; backup encryption/key recovery; timed restore RTO/RPO; authenticated external audit provenance; signed receipts; off-host disaster recovery; container/service rollback; simultaneous multi-host writers. \`PRAGMA quick_check\` and logical SQLite replay do not replace physical failure testing.

## Completeness review

| Area | Evidence/state | Release call |
| --- | --- | --- |
| Core boot and offline memory/evidence proofs | Real Core source and four-platform CI, see \`README.md\` and \`brain-smoke.yml\` | **Developer-beta candidate** |
| Per-database audit mirror and crash-gap reconciliation | \`bean/memory/audit_mirror.py\` and adversarial regression | **Code-level checked**, source authenticity still absent |
| Consistent snapshots, tamper flags, restore-copy drill | This PR and \`test_verified_backup.py\` | **Code-level checked** once CI green; operational exercise outstanding |
| Causal memory advantage over matched controls | Lab 026 research branch, four-arm real-model experiment inconclusive | **Research only**, not ready for Core claim |
| Neural learning/neuroevolution superiority | Sealed-seed trials mixed, isolated draft branches | **Research only**, not on Main |
| ChatGPT/local MCP, Windows installer | Review branches, separate deployment/operator requirements | **Do not claim bundled general release** |
| Bridge/AIscend/robot behavior | Separate apps and emulator/research evidence | **Not release-qualified by Core's green tests** |
| Real-world source identity/action authorization | Host attestations, no independently authenticated evidence-to-action boundary | **Block unattended autonomy** |
| Threat model, support, incident response, dependency/SBOM, secret scanning, license | Partial or missing release artifacts; repository is public without a redistribution license | **Block general production distribution** |
| Compatibility docs | Root ARCHITECTURE.md marked historical; README_INSTALL.md required replacement | **Documentation maintenance in this PR** |

**Release decision:** BEAN Core remains a **developer/experimental technical beta**, with improved local backup recovery discipline. An unattended commercial service, autonomous robot, trading operator, or production multi-tenant deployment is **not** release-qualified. No green test or learning lab result can override that judgment.
