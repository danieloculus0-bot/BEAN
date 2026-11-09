"""Reproducible negative control for interrupted multi-archive checkpoint publication.

Expected failure documents the current mutable-archive publication defect.
Uses disposable synthetic SQLite files; never touches the committed brain.
"""
from pathlib import Path
import sqlite3

import pytest

from scripts import invoke_bean as runner


def _db(path: Path, value: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
        conn.execute("INSERT INTO evidence VALUES (?)", (value,))


@pytest.mark.xfail(strict=True, reason="mutable archives are replaced before manifest commit")
def test_second_archive_replace_failure_preserves_prior_restart(tmp_path, monkeypatch):
    state = tmp_path / "state"
    first = tmp_path / "first"
    first.mkdir()
    for filename in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        _db(first / filename, "original")
    original = runner.checkpoint(state, first, None, 1, 3, 2, 12)
    manifest_before = (state / "manifest.json").read_bytes()

    next_runtime = tmp_path / "next"
    next_runtime.mkdir()
    runner.unpack(state, next_runtime)
    for filename in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        with sqlite3.connect(next_runtime / filename) as conn:
            conn.execute("INSERT INTO evidence VALUES ('updated')")

    real_replace = Path.replace
    def fail_second_archive(self, target):
        if str(target).endswith("bean_reasoning.sqlite3.gz"):
            raise OSError("synthetic injected filesystem failure")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_archive)
    with pytest.raises(OSError, match="synthetic injected"):
        runner.checkpoint(state, next_runtime, original, 2, 8, 2, 12)
    monkeypatch.setattr(Path, "replace", real_replace)

    assert (state / "manifest.json").read_bytes() == manifest_before
    restart = tmp_path / "restart"
    restart.mkdir()
    recovered = runner.unpack(state, restart)
    assert recovered["receipt_sha256"] == original["receipt_sha256"]
