"""Reproducible negative control for interrupted multi-archive checkpoint publication.

Tests immutable generation archives under interrupted publication.
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
        if str(target).endswith("bean_reasoning.sqlite3.gz.g00002"):
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

def test_successful_generation_restart(tmp_path):
    state = tmp_path / "state"
    first = tmp_path / "first"
    first.mkdir()
    for filename in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        _db(first / filename, "initial")
    first_receipt = runner.checkpoint(state, first, None, 1, 3, 2, 12)
    second = tmp_path / "second"
    second.mkdir()
    runner.unpack(state, second)
    for filename in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        with sqlite3.connect(second / filename) as conn:
            conn.execute("INSERT INTO evidence VALUES ('next')")
    second_receipt = runner.checkpoint(state, second, first_receipt, 2, 8, 2, 12)
    assert second_receipt["previous_receipt_sha256"] == first_receipt["receipt_sha256"]
    assert (state / first_receipt["databases"]["core"]["archive"]).exists()
    recovered_dir = tmp_path / "recovered"
    recovered_dir.mkdir()
    assert runner.unpack(state, recovered_dir)["generation"] == 2
    with sqlite3.connect(recovered_dir / "bean_memory.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2

def test_retry_after_interrupted_publication(tmp_path, monkeypatch):
    state, seed = tmp_path / "state", tmp_path / "seed"
    seed.mkdir()
    for name in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        _db(seed / name, "initial")
    prior = runner.checkpoint(state, seed, None, 1, 3, 2, 12)
    next_runtime = tmp_path / "next"
    next_runtime.mkdir()
    runner.unpack(state, next_runtime)
    for name in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        with sqlite3.connect(next_runtime / name) as db:
            db.execute("INSERT INTO evidence VALUES ('updated')")
    original_replace = Path.replace
    def interrupt(self, target):
        if str(target).endswith("bean_reasoning.sqlite3.gz.g00002"):
            raise OSError("injected interruption")
        return original_replace(self, target)
    monkeypatch.setattr(Path, "replace", interrupt)
    with pytest.raises(OSError, match="injected interruption"):
        runner.checkpoint(state, next_runtime, prior, 2, 8, 2, 12)
    monkeypatch.setattr(Path, "replace", original_replace)
    orphan = state / "bean_memory.sqlite3.gz.g00002"
    saved = orphan.read_bytes()
    before_retry = tmp_path / "before_retry"
    before_retry.mkdir()
    assert runner.unpack(state, before_retry)["generation"] == 1
    result = runner.checkpoint(state, next_runtime, prior, 2, 8, 2, 12)
    assert result["generation"] == 2
    assert orphan.read_bytes() == saved
    after_retry = tmp_path / "after_retry"
    after_retry.mkdir()
    assert runner.unpack(state, after_retry)["generation"] == 2


def test_conflicting_orphan_rejected_without_mutation(tmp_path):
    state, seed = tmp_path / "state", tmp_path / "seed"
    seed.mkdir()
    for name in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        _db(seed / name, "initial")
    prior = runner.checkpoint(state, seed, None, 1, 3, 2, 12)
    orphan = state / "bean_memory.sqlite3.gz.g00002"
    orphan.write_bytes(b"synthetic conflict")
    before = (state / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="conflicts with retry"):
        runner.checkpoint(state, seed, prior, 2, 8, 2, 12)
    assert orphan.read_bytes() == b"synthetic conflict"
    assert (state / "manifest.json").read_bytes() == before
    recovered = tmp_path / "recovered"
    recovered.mkdir()
    assert runner.unpack(state, recovered)["generation"] == 1


def test_fresh_boot_after_interruption_rejects_changed_orphan(tmp_path, monkeypatch):
    """Negative control: a new boot cannot silently reuse a stale generation."""
    state, seed = tmp_path / "state", tmp_path / "seed"
    seed.mkdir()
    for name in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        _db(seed / name, "initial")
    prior = runner.checkpoint(state, seed, None, 1, 3, 2, 12)

    interrupted = tmp_path / "interrupted"
    interrupted.mkdir()
    runner.unpack(state, interrupted)
    for name in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        with sqlite3.connect(interrupted / name) as db:
            db.execute("INSERT INTO evidence VALUES ('boot-A')")

    real_replace = Path.replace
    def interrupt(self, target):
        if str(target).endswith("bean_reasoning.sqlite3.gz.g00002"):
            raise OSError("injected interruption")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt)
    with pytest.raises(OSError, match="injected interruption"):
        runner.checkpoint(state, interrupted, prior, 2, 8, 2, 12)
    monkeypatch.setattr(Path, "replace", real_replace)

    orphan = state / "bean_memory.sqlite3.gz.g00002"
    orphan_before = orphan.read_bytes()
    manifest_before = (state / "manifest.json").read_bytes()

    # Simulate a new process loading only the last committed generation.
    fresh_boot = tmp_path / "fresh_boot"
    fresh_boot.mkdir()
    restored = runner.unpack(state, fresh_boot)
    assert restored["receipt_sha256"] == prior["receipt_sha256"]
    for name in ("bean_memory.sqlite3", "bean_reasoning.sqlite3"):
        with sqlite3.connect(fresh_boot / name) as db:
            db.execute("INSERT INTO evidence VALUES ('boot-B')")

    with pytest.raises(ValueError, match="conflicts with retry"):
        runner.checkpoint(state, fresh_boot, restored, 2, 8, 2, 12)
    assert orphan.read_bytes() == orphan_before
    assert (state / "manifest.json").read_bytes() == manifest_before

    recovery = tmp_path / "recovery"
    recovery.mkdir()
    assert runner.unpack(state, recovery)["generation"] == 1
