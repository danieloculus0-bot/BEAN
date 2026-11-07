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
    blob = saved / "bean_memory.sqlite3.gz"
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


def test_interrupted_archive_publication_invalidates_previous_local_generation(tmp_path, monkeypatch):
    """Negative control: local partial publication is not recoverable yet.

    This is a reproducible failure receipt, not a successful recovery test.
    GitHub commits are separate atomic publication boundaries; this tests
    the checkpoint() function's *local* interruption behavior only.
    """
    state = tmp_path / "state"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    _sqlite(runtime / "bean_memory.sqlite3", "generation-one-core")
    _sqlite(runtime / "bean_reasoning.sqlite3", "generation-one-reasoning")
    first = checkpoint(state, runtime, None, 1, 3, 2, 12)
    old_manifest = (state / "manifest.json").read_bytes()

    # Modify the next Core database so that a replacement archive has a
    # genuinely different digest; keep the reasoning database unchanged.
    with sqlite3.connect(str(runtime / "bean_memory.sqlite3")) as db:
        db.execute("INSERT INTO observations(value) VALUES ('generation-two')")
        db.commit()

    original_replace = Path.replace
    def interrupt_before_reasoning_archive(self, target):
        if str(self).endswith("bean_reasoning.sqlite3.gz.tmp"):
            raise OSError("synthetic interruption after first archive replacement")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt_before_reasoning_archive)
    with pytest.raises(OSError, match="synthetic interruption"):
        checkpoint(state, runtime, first, 2, 7, 2, 12)
    monkeypatch.setattr(Path, "replace", original_replace)

    # The old manifest remains, but its Core hash no longer matches.
    assert (state / "manifest.json").read_bytes() == old_manifest
    with pytest.raises(ValueError, match="hash or size mismatch"):
        unpack(state, tmp_path / "restored")
