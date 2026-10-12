"""Cross-platform recovery evidence for BEAN's verified backup bundles.

These tests use disposable real Core SQLite stores, not prewritten pass output.
They do not simulate an unclean power cut or independently authenticate evidence.
"""
from __future__ import annotations

import json
import shutil
import sqlite3

import pytest

from bean.memory.audit_mirror import mirror_path
from bean.memory.event_logger import EventType, Source, log_event
from bean.memory.store import get_store, init_store
from scripts.bean_backup import BackupError, create_backup, main, verify_backup


def seeded_store(tmp_path):
    db = tmp_path / "live" / "bean_memory.db"
    init_store(str(db))
    for n in range(3):
        log_event("backup-fixture", EventType.OBSERVATION,
                  f"documented event {n}", Source.SYSTEM, data={"iteration": n})
    return db


def test_live_wal_backup_has_valid_manifest_and_restores_event_history(tmp_path):
    db = seeded_store(tmp_path)
    # The Core store remains open in WAL mode while a separate connection backs up.
    assert get_store().fetchone("PRAGMA journal_mode")[0] == "wal"
    bundle = create_backup(db, tmp_path / "backups")
    assert {"memory.db", "memory.db.events.jsonl", "manifest.json"} == {
        f.name for f in bundle.iterdir()
    }
    result = verify_backup(bundle)
    assert result["status"] == "verified"
    assert result["restore_drill"] == "passed"
    assert result["snapshot"]["events"] == 3
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_audit_mirror"].startswith("not_asserted")
    assert manifest["provenance"].startswith("local hash only")

    restored = tmp_path / "reopened" / "bean_memory.db"
    restored.parent.mkdir()
    shutil.copy2(bundle / "memory.db", restored)
    shutil.copy2(bundle / "memory.db.events.jsonl", mirror_path(restored))
    init_store(str(restored))  # Reconcile Core's real audit mirror on boot.
    summaries = [r["summary"] for r in get_store().fetchall(
        "SELECT summary FROM events ORDER BY id"
    )]
    assert summaries == [f"documented event {n}" for n in range(3)]


def test_same_second_backups_never_overwrite_each_other(tmp_path):
    db = seeded_store(tmp_path)
    first = create_backup(db, tmp_path / "backups")
    second = create_backup(db, tmp_path / "backups")
    assert first != second
    assert verify_backup(first)["snapshot"] == verify_backup(second)["snapshot"]


def test_backup_tampering_rejected_even_if_db_is_readable(tmp_path):
    db = seeded_store(tmp_path)
    bundle = create_backup(db, tmp_path / "backups")
    mirror = bundle / "memory.db.events.jsonl"
    mirror.write_bytes(mirror.read_bytes().replace(b"documented", b"falsified"))
    with pytest.raises(BackupError, match="mirror SHA256 mismatch"):
        verify_backup(bundle)
    assert main(["--verify", str(bundle)]) == 1


def test_database_tampering_rejected_before_restore(tmp_path):
    db = seeded_store(tmp_path)
    bundle = create_backup(db, tmp_path / "backups")
    backup = bundle / "memory.db"
    with backup.open("ab") as out:
        out.write(b"tamper")
    with pytest.raises(BackupError, match="database SHA256 mismatch"):
        verify_backup(bundle)


def test_incomplete_and_missing_databases_never_publish_bundles(tmp_path):
    dest = tmp_path / "backups"
    with pytest.raises(BackupError, match="not found"):
        create_backup(tmp_path / "absent.db", dest)
    damaged = tmp_path / "not-sqlite.db"
    damaged.write_bytes(b"not a database")
    with pytest.raises((BackupError, sqlite3.DatabaseError)):
        create_backup(damaged, dest)
    assert not any(dest.iterdir())


def test_invalid_schema_is_rejected_not_called_a_success(tmp_path):
    db = tmp_path / "other.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE arbitrary (id INTEGER)")
    with pytest.raises(BackupError, match="complete BEAN"):
        create_backup(db, tmp_path / "backups")


def test_cli_creates_and_verifies_genuine_bundle(tmp_path, capsys):
    db = seeded_store(tmp_path)
    backups = tmp_path / "backup output"
    assert main(["--db", str(db), "--backup-dir", str(backups)]) == 0
    result = capsys.readouterr().out
    assert "verified and written" in result
    bundles = list(backups.iterdir())
    assert len(bundles) == 1
    assert main(["--verify", str(bundles[0])]) == 0
    assert '"restore_drill": "passed"' in capsys.readouterr().out
