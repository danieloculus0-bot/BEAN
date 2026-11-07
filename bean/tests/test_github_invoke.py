"""GitHub invocation and versioned synthetic BEAN state integrity."""
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.invoke_bean import checkpoint, digest, unpack


def _sqlite(path: Path, text: str) -> None:
    with sqlite3.connect(str(path)) as db:
        db.execute("CREATE TABLE observations (value TEXT)")
        db.execute("INSERT INTO observations(value) VALUES (?)", (text,))
        db.commit()


def test_public_checkpoint_survives_restart_without_reset(tmp_path):
    saved = tmp_path / "repo" / "research" / "github_brain"
    runtime = tmp_path / "first"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "synthetic-memory")
    _sqlite(runtime / "bean_reasoning.sqlite3", "synthetic-reasoning")
    initial = checkpoint(saved, runtime, None, 1, 5, 2, 12)
    assert initial["generation"] == 1
    assert initial["synthetic_only"] is True
    assert initial["model_weights_trained"] is False
    assert initial["previous_receipt_sha256"] is None
    restored = tmp_path / "later"
    restored.mkdir()
    loaded = unpack(saved, restored)
    assert loaded["receipt_sha256"] == initial["receipt_sha256"]
    for filename, expected in [
        ("bean_memory.sqlite3", "synthetic-memory"),
        ("bean_reasoning.sqlite3", "synthetic-reasoning"),
    ]:
        with sqlite3.connect(str(restored / filename)) as db:
            assert db.execute("SELECT value FROM observations").fetchone()[0] == expected
    updated = checkpoint(saved, restored, loaded, 2, 9, 2, 12)
    assert updated["generation"] == 2
    assert updated["previous_receipt_sha256"] == initial["receipt_sha256"]


def test_fail_closed_on_corrupt_compressed_memory(tmp_path):
    saved = tmp_path / "state"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "synthetic")
    _sqlite(runtime / "bean_reasoning.sqlite3", "synthetic")
    checkpoint(saved, runtime, None, 1, 3, 2, 12)
    blob = saved / "bean_memory.sqlite3.g000001.gz"
    blob.write_bytes(blob.read_bytes()[:-5] + b"wrong")
    with pytest.raises((ValueError, EOFError, OSError)):
        unpack(saved, tmp_path / "fresh")


def test_fail_closed_if_manifest_missing_or_forged(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / "bean_memory.sqlite3.gz").write_bytes(b"orphan")
    with pytest.raises(ValueError, match="orphaned"):
        unpack(state, tmp_path / "fresh")
    (state / "bean_memory.sqlite3.gz").unlink()
    (state / "manifest.json").write_text(
        json.dumps({"schema": "bean.github.invoke.v1", "generation": 999,
                    "synthetic_only": True, "receipt_sha256": digest(b"fake")}))
    with pytest.raises(ValueError, match="receipt mismatch"):
        unpack(state, tmp_path / "fresh")


def test_interrupted_archive_publication_preserves_previous_generation(tmp_path, monkeypatch):
    """Fault injection must leave the old manifest and both archives recoverable."""
    state = tmp_path / "state"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "generation-one-core")
    _sqlite(runtime / "bean_reasoning.sqlite3", "generation-one-reasoning")
    first = checkpoint(state, runtime, None, 1, 3, 2, 12)
    old_manifest = (state / "manifest.json").read_bytes()
    with sqlite3.connect(str(runtime / "bean_memory.sqlite3")) as db:
        db.execute("INSERT INTO observations(value) VALUES ('generation-two')")
        db.commit()

    original_replace = Path.replace
    def interrupt_before_reasoning_archive(self, target):
        if str(self).endswith("bean_reasoning.sqlite3.g000002.gz.tmp"):
            raise OSError("synthetic interruption after first archive publication")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt_before_reasoning_archive)
    with pytest.raises(OSError, match="synthetic interruption"):
        checkpoint(state, runtime, first, 2, 7, 2, 12)
    monkeypatch.setattr(Path, "replace", original_replace)
    assert (state / "manifest.json").read_bytes() == old_manifest
    restored = tmp_path / "restored"
    restored.mkdir()
    recovered = unpack(state, restored)
    assert recovered["receipt_sha256"] == first["receipt_sha256"]
    with sqlite3.connect(str(restored / "bean_memory.sqlite3")) as db:
        assert db.execute("SELECT value FROM observations").fetchall() == [("generation-one-core",)]
    with sqlite3.connect(str(restored / "bean_reasoning.sqlite3")) as db:
        assert db.execute("SELECT value FROM observations").fetchall() == [("generation-one-reasoning",)]


def test_legacy_checkpoint_archive_names_remain_readable(tmp_path):
    state = tmp_path / "state"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "legacy-core")
    _sqlite(runtime / "bean_reasoning.sqlite3", "legacy-reasoning")
    first = checkpoint(state, runtime, None, 1, 3, 2, 12)
    for name, record in first["databases"].items():
        old_name = "bean_memory.sqlite3.gz" if name == "core" else "bean_reasoning.sqlite3.gz"
        (state / record["archive"]).rename(state / old_name)
        del record["archive"]
    from scripts.invoke_bean import canonical
    first["receipt_sha256"] = digest(canonical({k: v for k, v in first.items() if k != "receipt_sha256"}))
    (state / "manifest.json").write_text(json.dumps(first))
    restored = tmp_path / "restored"
    restored.mkdir()
    assert unpack(state, restored)["receipt_sha256"] == first["receipt_sha256"]


def test_interrupted_generation_retry_with_changed_bytes_fails_closed(tmp_path, monkeypatch):
    """A stale generation archive must not be silently overwritten on retry."""
    state = tmp_path / "state"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "original-core")
    _sqlite(runtime / "bean_reasoning.sqlite3", "original-reasoning")
    first = checkpoint(state, runtime, None, 1, 3, 2, 12)
    original_manifest = (state / "manifest.json").read_bytes()

    with sqlite3.connect(str(runtime / "bean_memory.sqlite3")) as db:
        db.execute("INSERT INTO observations(value) VALUES ('first-attempt')")
    original_replace = Path.replace

    def interrupt_before_reasoning(self, target):
        if str(self).endswith("bean_reasoning.sqlite3.g000002.gz.tmp"):
            raise OSError("synthetic interruption")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt_before_reasoning)
    with pytest.raises(OSError, match="synthetic interruption"):
        checkpoint(state, runtime, first, 2, 7, 2, 12)
    monkeypatch.setattr(Path, "replace", original_replace)

    with sqlite3.connect(str(runtime / "bean_memory.sqlite3")) as db:
        db.execute("INSERT INTO observations(value) VALUES ('changed-retry')")
    with pytest.raises(ValueError, match="generation already exists with different contents"):
        checkpoint(state, runtime, first, 2, 8, 2, 12)
    assert (state / "manifest.json").read_bytes() == original_manifest

    recovered_dir = tmp_path / "recovered"
    recovered_dir.mkdir()
    assert unpack(state, recovered_dir)["receipt_sha256"] == first["receipt_sha256"]
    with sqlite3.connect(str(recovered_dir / "bean_memory.sqlite3")) as db:
        assert db.execute("SELECT value FROM observations").fetchall() == [("original-core",)]


def test_manifest_publish_interruption_retries_identical_generation(tmp_path, monkeypatch):
    """Archives staged before manifest publication must be safely reusable."""
    state = tmp_path / "state"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "initial-core")
    _sqlite(runtime / "bean_reasoning.sqlite3", "initial-reasoning")
    first = checkpoint(state, runtime, None, 1, 3, 2, 12)
    original_manifest = (state / "manifest.json").read_bytes()

    with sqlite3.connect(str(runtime / "bean_memory.sqlite3")) as db:
        db.execute("INSERT INTO observations(value) VALUES ('next-generation')")

    original_replace = Path.replace

    def interrupt_manifest(self, target):
        if str(self).endswith("manifest.json.tmp"):
            raise OSError("synthetic interruption before manifest publication")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt_manifest)
    with pytest.raises(OSError, match="synthetic interruption"):
        checkpoint(state, runtime, first, 2, 7, 2, 12)
    monkeypatch.setattr(Path, "replace", original_replace)

    assert (state / "manifest.json").read_bytes() == original_manifest
    recovered = tmp_path / "recovered"
    recovered.mkdir()
    assert unpack(state, recovered)["receipt_sha256"] == first["receipt_sha256"]

    second = checkpoint(state, runtime, first, 2, 7, 2, 12)
    assert second["generation"] == 2
    assert second["previous_receipt_sha256"] == first["receipt_sha256"]
    restarted = tmp_path / "restarted"
    restarted.mkdir()
    assert unpack(state, restarted)["receipt_sha256"] == second["receipt_sha256"]
    with sqlite3.connect(str(restarted / "bean_memory.sqlite3")) as db:
        assert db.execute("SELECT value FROM observations ORDER BY rowid").fetchall() == [
            ("initial-core",), ("next-generation",)
        ]
