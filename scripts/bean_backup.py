#!/usr/bin/env python3
"""Consistent, independently verifiable BEAN SQLite backup bundles.

SQLite is the source of truth. A backup's JSONL mirror is reconstructed from
its *snapshot*, not copied from a live sidecar that may have different timing.
This is an integrity/recovery drill, not authenticated provenance or disaster
recovery proof from physical power loss.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import uuid


class BackupError(RuntimeError):
    pass


def load_env(path: str = "/etc/bean/bean.env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise BackupError(f"database file does not exist: {path}")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot_receipt(db: Path) -> tuple[dict, bytes]:
    with closing(_connect_readonly(db)) as conn:
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise BackupError("SQLite quick_check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise BackupError("SQLite foreign_key_check failed")
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"events", "sessions", "identity"}.issubset(names):
            raise BackupError("not a complete BEAN Core memory schema")
        entries = []
        try:
            rows = conn.execute("SELECT id, session_uuid, event_uuid, event_type, subtype, "
                                "summary, data, source, severity, created_at "
                                "FROM events ORDER BY id")
            for row in rows:
                payload = {
                    "id": row["id"], "session_uuid": row["session_uuid"],
                    "event_uuid": row["event_uuid"], "event_type": row["event_type"],
                    "subtype": row["subtype"], "summary": row["summary"],
                    "source": row["source"], "severity": row["severity"],
                    "data": json.loads(row["data"]) if row["data"] is not None else None,
                    "ts": row["created_at"],
                }
                entries.append((json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                           separators=(",", ":")) + "\n").encode("utf-8"))
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise BackupError("BEAN events cannot be faithfully serialized") from exc
        mirror = b"".join(entries)
        return {"events": len(entries), "last_event_id": payload["id"] if entries else None,
                "event_stream_sha256": hashlib.sha256(mirror).hexdigest()}, mirror


def _sync_write(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != "nt":
        path.chmod(0o600)


def _restore_drill(db: Path, expected: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="bean-restore-drill-") as directory:
        restored = Path(directory) / "restored.db"
        with closing(_connect_readonly(db)) as source, closing(sqlite3.connect(restored)) as target:
            source.backup(target)
        receipt, _ = _snapshot_receipt(restored)
        if receipt != expected:
            raise BackupError("restored SQLite content differs from backed-up snapshot")


def verify_backup(bundle: str | Path) -> dict:
    bundle = Path(bundle)
    try:
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        db = bundle / "memory.db"
        mirror_path = bundle / "memory.db.events.jsonl"
        if manifest.get("schema") != "bean.backup.v1":
            raise BackupError("unknown backup schema")
        if _digest(db) != manifest["db_sha256"]:
            raise BackupError("database SHA256 mismatch")
        if _digest(mirror_path) != manifest["mirror_sha256"]:
            raise BackupError("audit mirror SHA256 mismatch")
        receipt, canonical = _snapshot_receipt(db)
        if receipt != manifest.get("snapshot") or canonical != mirror_path.read_bytes():
            raise BackupError("backup event stream disagrees with audit mirror")
        _restore_drill(db, receipt)
        return {"status": "verified", "snapshot": receipt,
                "restore_drill": "passed", "bundle": str(bundle)}
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        raise BackupError("backup verification failed: " + str(exc)) from exc


def create_backup(db_path: str | Path, backup_dir: str | Path) -> Path:
    db_path, backup_dir = Path(db_path), Path(backup_dir)
    if not db_path.is_file():
        raise BackupError(f"BEAN DB not found: {db_path}")
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique = uuid.uuid4().hex[:12]
    target = backup_dir / f"bean_memory_{stamp}_{unique}"
    stage = Path(tempfile.mkdtemp(prefix=".bean-backup-partial-", dir=backup_dir))
    try:
        backup_db = stage / "memory.db"
        with closing(_connect_readonly(db_path)) as source, closing(sqlite3.connect(backup_db)) as dest:
            source.backup(dest, pages=256, sleep=0.05)
        if os.name != "nt":
            backup_db.chmod(0o600)
        receipt, mirror = _snapshot_receipt(backup_db)
        _sync_write(stage / "memory.db.events.jsonl", mirror)
        manifest = {
            "schema": "bean.backup.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "snapshot": receipt,
            "db_sha256": _digest(backup_db),
            "mirror_sha256": _digest(stage / "memory.db.events.jsonl"),
            "source_audit_mirror": "not_asserted; mirror reconstructed from consistent SQLite snapshot",
            "provenance": "local hash only; not digitally signed",
        }
        _sync_write(stage / "manifest.json",
                    (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        verify_backup(stage)  # Includes a backup-to-restore-copy drill.
        stage.rename(target)  # Publish complete bundle; partial stages never appear as releases.
        if os.name != "nt":
            fd = os.open(str(backup_dir), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return target
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="Source SQLite database; defaults to BEAN_DB_PATH")
    parser.add_argument("--backup-dir", help="Destination; defaults to BEAN_BACKUP_DIR")
    parser.add_argument("--verify", metavar="BUNDLE", help="Validate a completed backup and exercise restore-copy")
    args = parser.parse_args(argv)
    load_env()
    try:
        if args.verify:
            print(json.dumps(verify_backup(args.verify), sort_keys=True))
        else:
            path = Path(args.db or os.environ.get("BEAN_DB_PATH", "/home/bean/bean_data/bean_memory.db"))
            backup_dir = Path(args.backup_dir or os.environ.get("BEAN_BACKUP_DIR", str(path.parent / "backups")))
            bundle = create_backup(path, backup_dir)
            print(f"BEAN memory backup verified and written: {bundle}")
        return 0
    except (BackupError, OSError, sqlite3.Error) as exc:
        print(f"BEAN backup FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
