"""Adversarial tests of BEAN's real SQLite / JSONL audit gap and recovery.

All records are fictional and live in disposable per-test databases.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from bean.memory import audit_mirror
from bean.memory.audit_mirror import (
    AuditMirrorError, mirror_path, reconcile_event_mirror,
)
from bean.memory.event_logger import EventType, log_event, Source
from bean.memory.store import get_store, init_store


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in mirror_path(path).read_text(encoding="utf-8").splitlines()]


def test_restart_recovers_a_committed_event_after_simulated_mirror_io_failure(
    tmp_path, monkeypatch
):
    db = tmp_path / "interrupted.sqlite"
    init_store(str(db))
    original_lock = audit_mirror._writer_lock

    def failed_open(path):
        raise PermissionError("synthetic read-only mirror location")

    monkeypatch.setattr(audit_mirror, "_writer_lock", failed_open)
    with pytest.raises(AuditMirrorError, match="Committed BEAN event id="):
        log_event("fixture-session", EventType.OBSERVATION,
                  "the SQLite commit must survive the mirror outage", Source.SYSTEM)
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"] == 1
    assert _rows(db) == []  # only the old empty mirror is present
    monkeypatch.setattr(audit_mirror, "_writer_lock", original_lock)

    # Fresh init must repair WITHOUT caller replaying the already committed event.
    init_store(str(db))
    rows = _rows(db)
    assert len(rows) == 1
    assert rows[0]["summary"] == "the SQLite commit must survive the mirror outage"
    assert reconcile_event_mirror()["appended"] == 0
    assert len(_rows(db)) == 1


def test_partial_tail_is_repaired_from_sqlite_after_restart(tmp_path):
    db = tmp_path / "crash.sqlite"
    init_store(str(db))
    log_event("session", EventType.OBSERVATION, "one", Source.SYSTEM)
    log_event("session", EventType.OBSERVATION, "two", Source.SYSTEM)
    path = mirror_path(db)
    complete = path.read_bytes()
    path.write_bytes(complete[:-14])  # simulated interrupted append/fsync
    assert not path.read_bytes().endswith(b"\n")

    init_store(str(db))
    assert path.read_bytes() == complete
    assert [row["summary"] for row in _rows(db)] == ["one", "two"]
    assert reconcile_event_mirror()["appended"] == 0


def test_altered_complete_audit_history_fails_closed(tmp_path):
    db = tmp_path / "tamper.sqlite"
    init_store(str(db))
    log_event("session", EventType.OBSERVATION, "original", Source.SYSTEM)
    path = mirror_path(db)
    path.write_bytes(path.read_bytes().replace(b"original", b"falsified"))
    with pytest.raises(AuditMirrorError, match="history mismatch"):
        init_store(str(db))
    # No rewrite performed to hide the problem; authoritative DB still intact.
    assert b"falsified" in path.read_bytes()
    assert get_store().fetchone("SELECT summary FROM events")["summary"] == "original"


def test_missing_mirror_rebuilds_without_losing_events(tmp_path):
    db = tmp_path / "missing.sqlite"
    init_store(str(db))
    log_event("session", EventType.OBSERVATION, "retained", Source.SYSTEM)
    mirror_path(db).unlink()
    init_store(str(db))
    assert [r["summary"] for r in _rows(db)] == ["retained"]


def test_databases_are_isolated_not_written_to_package_directory(tmp_path):
    a, b = tmp_path / "a.sqlite", tmp_path / "b.sqlite"
    init_store(str(a))
    log_event("session", EventType.OBSERVATION, "from A", Source.SYSTEM)
    init_store(str(b))
    log_event("session", EventType.OBSERVATION, "from B", Source.SYSTEM)
    assert [r["summary"] for r in _rows(a)] == ["from A"]
    assert [r["summary"] for r in _rows(b)] == ["from B"]
    assert mirror_path(a) != mirror_path(b)
    assert mirror_path(a).parent == tmp_path


def test_multiple_python_processes_append_without_duplicate_or_missing_uuids(tmp_path):
    db = tmp_path / "shared.sqlite"
    init_store(str(db))
    get_store().close()
    code = (
        "import sys; "
        "from bean.memory.store import init_store; "
        "from bean.memory.event_logger import log_event, EventType, Source; "
        "init_store(sys.argv[1]); "
        "[(log_event(sys.argv[2], EventType.OBSERVATION, "
        "sys.argv[2]+'-'+str(i), Source.SYSTEM)) for i in range(10)]"
    )
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    a = subprocess.Popen([sys.executable, "-c", code, str(db), "procA"],
                         cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    b = subprocess.Popen([sys.executable, "-c", code, str(db), "procB"],
                         cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for child in (a, b):
        out, err = child.communicate(timeout=35)
        if child.returncode != 0:
            # Print the ORIGINAL child traceback as separate captured stdout.
            # Do not let pytest truncate it inside AssertionError repr.
            print("CHILD_STDOUT:\n" + out.decode(errors="replace"))
            print("CHILD_STDERR:\n" + err.decode(errors="replace"))
        assert child.returncode == 0
    init_store(str(db))
    rows = _rows(db)
    uuids = [row["event_uuid"] for row in rows]
    assert len(rows) == len(set(uuids)) == 20
    assert {row["summary"] for row in rows} == {
        f"{label}-{i}" for label in ("procA", "procB") for i in range(10)
    }
    assert [row["id"] for row in rows] == sorted(row["id"] for row in rows)


def test_orphan_audit_record_is_not_silently_accepted(tmp_path):
    db = tmp_path / "orphan.sqlite"
    init_store(str(db))
    log_event("session", EventType.OBSERVATION, "known", Source.SYSTEM)
    with mirror_path(db).open("ab") as handle:
        handle.write(b'{"event_uuid":"forged"}\n')
    with pytest.raises(AuditMirrorError, match="absent from the current SQLite"):
        reconcile_event_mirror()
