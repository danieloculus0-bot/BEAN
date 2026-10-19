"""
bean/memory/store.py

The memory store. SQLite-backed. WAL mode. Boring on purpose.
This is the only thing allowed to touch the database file directly.
Everything else goes through this module.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional


_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "memory_schema.sql"

# The initialized global Core store retains its historical thread-local handle.
# Independently constructed MemoryStore instances own separate handles.
_local = threading.local()


class MemoryStore:
    """
    Manages the BEAN SQLite memory database.
    
    Independent instances each own their thread-local connections.
    WAL mode enabled for concurrent reads during writes.
    """

    def __init__(self, db_path: str, *, _connection_local=None):
        self._local = _connection_local if _connection_local is not None else threading.local()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self):
        """Apply schema if not already applied. Idempotent."""
        schema = _SCHEMA_PATH.read_text()
        conn = self._conn()
        conn.executescript(schema)
        conn.commit()

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local connection, creating if needed."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return self._local.conn

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        return self._conn().execute(sql, params)

    def executemany(self, sql: str, params_list) -> sqlite3.Cursor:
        return self._conn().executemany(sql, params_list)

    def commit(self):
        self._conn().commit()

    def fetchone(self, sql: str, params=()) -> Optional[sqlite3.Row]:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params=()) -> list:
        return self.execute(sql, params).fetchall()

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Module-level singleton — initialized by runtime bootstrap
_store: Optional[MemoryStore] = None


def init_store(db_path: str) -> MemoryStore:
    """Switch the current thread to this database without leaking connections.

    A prior thread-local SQLite handle must never be reused for another
    MemoryStore path. Reinitialization is a host-controlled lifecycle
    operation; callers must finish/commit their work before switching DBs.
    Other threads must shut down their own connections independently.
    """
    global _store
    previous = getattr(_local, "conn", None)
    if previous is not None:
        previous.close()
        _local.conn = None
    _store = MemoryStore(db_path, _connection_local=_local)
    # Reconcile a committed event whose process previously crashed after the
    # SQLite commit but before JSONL fsync. Fail startup on mirror tampering or
    # unavailable mirror storage; never pretend the log is complete.
    from .audit_mirror import reconcile_event_mirror
    reconcile_event_mirror(_store)
    return _store


def get_store() -> MemoryStore:
    if _store is None:
        raise RuntimeError(
            "MemoryStore not initialized. Call init_store() first."
        )
    return _store
