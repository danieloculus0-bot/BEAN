"""Real SQLite/JSONL desktop-memory tests, including distinct Python processes.

All notes are fictional. This verifies persistence and withholding, not learning.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from bean.memory.audit_mirror import AuditMirrorError, mirror_path
from bean.voice.desktop_memory import DesktopMemory


def test_explicit_note_is_retained_across_new_core_sessions(tmp_path):
    db = tmp_path / "private BEAN" / "brain.db"
    a = DesktopMemory(db)
    assert a.recall("paddle") == []
    assert not db.exists()
    record = a.remember("Paddle is blue on the fictional robot")
    assert record["id"] > 0
    assert record["provenance"] == "user_submitted_unverified"
    assert mirror_path(db).is_file()
    restored = DesktopMemory(db).recall("paddle")
    assert len(restored) == 1
    assert restored[0]["id"] == record["id"]
    assert restored[0]["text"] == record["text"]
    assert restored[0]["provenance"] == "user_submitted_unverified"
    assert DesktopMemory(db).recall("never entered") == []


def test_two_distinct_python_processes_share_only_expected_note(tmp_path):
    db = tmp_path / "memory path with spaces" / "bean.db"
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    note = "Fixture memory: zebra-20261012-unique"
    writer = ("import sys; from bean.voice.desktop_memory import DesktopMemory; "
              "r=DesktopMemory(sys.argv[1]).remember(sys.argv[2]); "
              "print(r['id'])")
    w = subprocess.run([sys.executable, "-c", writer, str(db), note],
                       cwd=root, env=env, capture_output=True, text=True, timeout=30)
    assert w.returncode == 0, w.stderr
    event_id = int(w.stdout.strip())

    reader = ("import sys,json; from bean.voice.desktop_memory import DesktopMemory; "
              "print(json.dumps(DesktopMemory(sys.argv[1]).recall(sys.argv[2])))")
    r = subprocess.run([sys.executable, "-c", reader, str(db), "zebra-20261012-unique"],
                       cwd=root, env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    observations = json.loads(r.stdout)
    assert len(observations) == 1
    assert observations[0]["id"] == event_id
    assert observations[0]["text"] == note
    assert observations[0]["provenance"] == "user_submitted_unverified"


def test_unrelated_database_and_query_do_not_leak_saved_context(tmp_path):
    first = DesktopMemory(tmp_path / "a.sqlite")
    second = DesktopMemory(tmp_path / "b.sqlite")
    first.remember("The fictional torque setting is 42 N m")
    assert not second.recall("torque")
    assert "42" in first.context_for("torque")
    assert "42" not in first.context_for("soup")


def test_corrupted_audit_mirror_fails_closed_instead_of_spoofing_memory(tmp_path):
    db = tmp_path / "core.sqlite"
    memory = DesktopMemory(db)
    memory.remember("Fictional compressor last checked Tuesday")
    sidecar = mirror_path(db)
    before = sidecar.read_bytes()
    assert b"compressor" in before
    sidecar.write_bytes(before.replace(b"compressor", b"falsified!"))
    with pytest.raises(AuditMirrorError, match="history mismatch"):
        memory.recall("compressor")
    assert sidecar.read_bytes() != before


def test_empty_overlong_and_invalid_queries_do_not_write_or_promote(tmp_path):
    db = tmp_path / "empty.sqlite"
    memory = DesktopMemory(db)
    for note in ("", "   ", "x" * 801):
        with pytest.raises(ValueError):
            memory.remember(note)
    assert not db.exists()
    with pytest.raises(ValueError):
        memory.recall("x" * 201)
    with pytest.raises(ValueError):
        memory.recall(" ", limit=1)
    with pytest.raises(ValueError):
        memory.recall("hello", limit=100)
