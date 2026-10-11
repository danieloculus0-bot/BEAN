"""Regression: changing BEAN's active memory DB must not reuse stale thread-local SQLite."""
from bean.memory.store import get_store, init_store


def test_reinitializing_store_isolates_current_thread_connections(tmp_path):
    first = tmp_path / "memory_a.sqlite"
    second = tmp_path / "memory_b.sqlite"
    try:
        init_store(str(first))
        a = get_store()
        a.execute("CREATE TABLE sample_isolation (value INTEGER NOT NULL)")
        a.execute("INSERT INTO sample_isolation (value) VALUES (17)")
        a.commit()

        init_store(str(second))
        b = get_store()
        assert b.fetchone("PRAGMA database_list")[2].endswith("memory_b.sqlite")
        assert b.fetchone(
            "SELECT COUNT(*) AS n FROM sqlite_master WHERE name='sample_isolation'"
        )["n"] == 0

        init_store(str(first))
        assert get_store().fetchone(
            "SELECT value FROM sample_isolation LIMIT 1"
        )["value"] == 17
    finally:
        get_store().close()


def test_reinitialize_same_path_does_not_erase_committed_data(tmp_path):
    path = tmp_path / "same.sqlite"
    try:
        init_store(str(path))
        get_store().execute("CREATE TABLE persistent_probe (n INTEGER)")
        get_store().execute("INSERT INTO persistent_probe VALUES (3)")
        get_store().commit()
        init_store(str(path))
        assert get_store().fetchone("SELECT n FROM persistent_probe")["n"] == 3
    finally:
        get_store().close()
