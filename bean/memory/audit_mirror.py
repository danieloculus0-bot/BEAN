"""Reconcile BEAN's authoritative SQLite event rows with a per-database JSONL mirror.

Guarantees for this bounded, single-host implementation:
- SQLite is authoritative; a mirror error never rolls back a committed event.
- On startup and after writes, a missing or truncated *tail* is reconstructed.
- Existing complete rows are compared byte-for-byte with canonical SQLite
  serialization; modified history raises, rather than silently rewriting.
- An inter-process advisory lock serializes mirror writers; the DB is reread
  only after acquiring the lock. Writes flush and fsync before returning.
- A separate database uses a separate audit file, not the installed package.

Limitations: full-prefix checking is O(n) per event and not yet load-tested
at high throughput; external access to both DB and mirror is not authenticated.
This is not a cryptographic or WORM audit system.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Iterator

from .store import get_store, MemoryStore


class AuditMirrorError(RuntimeError):
    """SQLite is authoritative, but its JSONL mirror is not healthy."""


def mirror_path(database: str | Path) -> Path:
    return Path(str(Path(database).resolve()) + ".events.jsonl")


@contextmanager
def _writer_lock(path: Path) -> Iterator[None]:
    """OS-released cross-process advisory lock, including on crash."""
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            # Never READ the first byte before locking: Windows rejects a
            # read of a byte locked by another process. Size checks do not
            # access that locked data; the byte is created only when missing.
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"1")
                handle.flush()
            # On Windows a live competing byte-lock may report EACCES.
            # Retry only that contention signal; all other I/O failures remain
            # fatal and visible. A crashed process releases its Windows lock.
            deadline = time.monotonic() + 20.0
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN):
                        raise
                    if time.monotonic() >= deadline:
                        raise AuditMirrorError("Timed out waiting for Windows mirror lock") from exc
                    time.sleep(0.025)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _canonical_lines(store: MemoryStore) -> list[bytes]:
    rows = store.fetchall(
        "SELECT id, session_uuid, event_uuid, event_type, subtype, summary, "
        "data, source, severity, created_at FROM events ORDER BY id"
    )
    lines = []
    for row in rows:
        payload = {
            "id": row["id"], "session_uuid": row["session_uuid"],
            "event_uuid": row["event_uuid"], "event_type": row["event_type"],
            "subtype": row["subtype"], "summary": row["summary"],
            "source": row["source"], "severity": row["severity"],
            "data": json.loads(row["data"]) if row["data"] is not None else None,
            "ts": row["created_at"],
        }
        lines.append((json.dumps(payload, sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":"))
                      + "\n").encode("utf-8"))
    return lines


def _replace_atomic(path: Path, lines: list[bytes]) -> None:
    """Replace only with a complete fsynced snapshot in the same directory."""
    fd, temp_name = tempfile.mkstemp(prefix=".bean-mirror-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.writelines(lines)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        if os.name != "nt":
            # Durably commit the renamed directory entry where supported.
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def reconcile_event_mirror(store: MemoryStore | None = None) -> dict:
    """Recreate missing entries without duplicates; refuse historical tampering.

    A trailing partial line is recoverable only when it is exactly a byte
    prefix of the next authoritative event. Other mismatches fail closed.
    """
    store = store or get_store()
    path = mirror_path(store.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _writer_lock(path):
            expected = _canonical_lines(store)
            if not path.exists():
                _replace_atomic(path, expected)
                return {"status": "rebuilt_missing", "events": len(expected),
                        "appended": len(expected), "path": str(path)}
            current = path.read_bytes()
            full = current.splitlines(keepends=True)
            finished = [line for line in full if line.endswith(b"\n")]
            incomplete = len(finished) != len(full)
            if len(finished) > len(expected):
                raise AuditMirrorError("Mirror has events absent from the current SQLite store")
            for index, actual in enumerate(finished):
                if actual != expected[index]:
                    raise AuditMirrorError(
                        f"Mirror history mismatch at row {index + 1}; no data rewritten"
                    )
            if incomplete:
                if len(finished) >= len(expected) or not expected[len(finished)].startswith(full[-1]):
                    raise AuditMirrorError("Mirror has a non-recoverable trailing record")
                _replace_atomic(path, expected)
                return {"status": "repaired_partial_tail", "events": len(expected),
                        "appended": len(expected)-len(finished),
                        "path": str(path)}
            delta = expected[len(finished):]
            if delta:
                with path.open("ab") as handle:
                    handle.writelines(delta)
                    handle.flush()
                    os.fsync(handle.fileno())
            return {"status": "synchronized", "events": len(expected),
                    "appended": len(delta), "path": str(path)}
    except AuditMirrorError:
        raise
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise AuditMirrorError(
            f"SQLite events remain authoritative; JSONL mirror reconciliation failed: {exc}"
        ) from exc
