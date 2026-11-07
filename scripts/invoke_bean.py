#!/usr/bin/env python3
"""Invoke the real BEAN Python Core on a disposable GitHub runner.

Restore only this repository's public-safe synthetic SQLite checkpoints,
exercise the existing Core tick loop, and write checked, restartable state.
GitHub Actions publishes these bytes after successful tests; this module
never holds a GitHub write credential or invokes effectors.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = {
    "core": ("bean_memory.sqlite3.gz", "bean_memory.sqlite3"),
    "reasoning": ("bean_reasoning.sqlite3.gz", "bean_reasoning.sqlite3"),
}
MAX_COMPRESSED = 12 * 1024 * 1024
MAX_UNCOMPRESSED = 80 * 1024 * 1024
MANIFEST = "manifest.json"


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def check_sqlite(path: Path) -> None:
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("missing BEAN SQLite checkpoint")
    connection = sqlite3.connect(str(path))
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("BEAN SQLite checkpoint failed integrity check")
    finally:
        connection.close()


def unpack(state_dir: Path, runtime_dir: Path) -> dict | None:
    manifest_path = state_dir / MANIFEST
    if not manifest_path.exists():
        if any((state_dir / compressed).exists() for compressed, _ in CHECKPOINTS.values()):
            raise ValueError("orphaned BEAN checkpoint: refusing to reset memory")
        return None
    manifest_bytes = manifest_path.read_bytes()
    if len(manifest_bytes) > 16000:
        raise ValueError("oversized BEAN manifest")
    previous = json.loads(manifest_bytes)
    if (previous.get("schema") != "bean.github.invoke.v1"
            or previous.get("synthetic_only") is not True
            or type(previous.get("generation")) is not int
            or previous["generation"] < 1):
        raise ValueError("invalid BEAN checkpoint manifest")
    claimed = previous.get("receipt_sha256")
    unsigned = {k: v for k, v in previous.items() if k != "receipt_sha256"}
    if claimed != digest(canonical(unsigned)):
        raise ValueError("BEAN manifest receipt mismatch")
    for name, (archive, restored) in CHECKPOINTS.items():
        record = previous.get("databases", {}).get(name)
        if not isinstance(record, dict):
            raise ValueError("BEAN manifest missing database")
        compressed = state_dir / archive
        if not compressed.is_file() or compressed.stat().st_size > MAX_COMPRESSED:
            raise ValueError("missing or oversized BEAN compressed checkpoint")
        with gzip.open(compressed, "rb") as source:
            body = source.read(MAX_UNCOMPRESSED + 1)
        if len(body) > MAX_UNCOMPRESSED or digest(body) != record.get("sha256"):
            raise ValueError("BEAN compressed checkpoint hash or size mismatch")
        destination = runtime_dir / restored
        # A later boot must never replay a stale WAL sidecar from a prior process.
        for suffix in ("-wal", "-shm"):
            (runtime_dir / (restored + suffix)).unlink(missing_ok=True)
        destination.write_bytes(body)
        check_sqlite(destination)
    return previous


def sqlite_stats(core: Path) -> tuple[int, int, str, int]:
    check_sqlite(core)
    with sqlite3.connect(str(core)) as conn:
        boots = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        last = conn.execute(
            "SELECT session_uuid,shutdown_time FROM sessions ORDER BY boot_count DESC LIMIT 1"
        ).fetchone()
        if not last or not last[1]:
            raise ValueError("BEAN did not complete a clean session")
        handled = conn.execute(
            "SELECT COUNT(*) FROM events WHERE session_uuid=? "
            "AND subtype='inbox_command_processed'", (last[0],)
        ).fetchone()[0]
    return boots, events, last[0], handled


def checkpoint(state_dir: Path, runtime_dir: Path, prior: dict | None,
               boots: int, events: int, processed: int, ticks: int) -> dict:
    state_dir.mkdir(parents=True, exist_ok=True)
    databases = {}
    for name, (archive, filename) in CHECKPOINTS.items():
        path = runtime_dir / filename
        check_sqlite(path)
        # SQLite's backup API writes a consistent copy, never a live WAL stream.
        backup = runtime_dir / (filename + ".backup")
        with sqlite3.connect(str(path)) as source, sqlite3.connect(str(backup)) as target:
            source.backup(target)
        payload = backup.read_bytes()
        if len(payload) > MAX_UNCOMPRESSED:
            raise ValueError("BEAN memory exceeded public checkpoint size limit")
        compressed = gzip.compress(payload, mtime=0)
        if len(compressed) > MAX_COMPRESSED:
            raise ValueError("BEAN memory exceeded compressed checkpoint size limit")
        (state_dir / (archive + ".tmp")).write_bytes(compressed)
        (state_dir / (archive + ".tmp")).replace(state_dir / archive)
        databases[name] = {"sha256": digest(payload), "bytes": len(payload)}
        backup.unlink()
    source_sha = os.environ.get("GITHUB_SHA", "local-validation")
    if not (source_sha == "local-validation" or re.fullmatch(r"[0-9a-f]{40}", source_sha)):
        raise ValueError("invalid source revision")
    receipt = {
        "schema": "bean.github.invoke.v1",
        "synthetic_only": True,
        "generation": (prior["generation"] + 1 if prior else 1),
        "previous_receipt_sha256": prior["receipt_sha256"] if prior else None,
        "source_sha": source_sha,
        "github_run_id": os.environ.get("GITHUB_RUN_ID") or None,
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or None,
        "boots": boots,
        "events": events,
        "processed_digital_commands": processed,
        "ticks": ticks,
        "databases": databases,
        "model_weights_trained": False,
        "consciousness_proven": False,
        "scope": "synthetic digital Core runtime and restart continuity, not subjective experience",
    }
    receipt["receipt_sha256"] = digest(canonical(receipt))
    staging = state_dir / (MANIFEST + ".tmp")
    staging.write_bytes(json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    staging.replace(state_dir / MANIFEST)
    return receipt


def invoke(state_dir: Path, runtime_dir: Path, ticks: int = 12, hz: int = 20) -> dict:
    if not 2 <= ticks <= 120 or not 1 <= hz <= 30:
        raise ValueError("ticks must be 2..120 and hz 1..30")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    prior = unpack(state_dir, runtime_dir)
    core = runtime_dir / "bean_memory.sqlite3"
    reasoning = runtime_dir / "bean_reasoning.sqlite3"
    if prior is None and (core.exists() or reasoning.exists()):
        raise ValueError("uncheckpointed prior BEAN runtime found")
    inbox = runtime_dir / "inbox"
    inbox.mkdir(exist_ok=True)
    previously_processed = len(list((inbox / "processed").glob("*.json")))
    for path in inbox.glob("*.json"):
        raise ValueError("unexpected pending inbox command")
    commands = ("run_brain_maintenance", "update_models")
    arguments = ({"review_uncertainties": True}, {"trigger": "github_digital_tick"})
    generation = prior["generation"] + 1 if prior else 1
    for number, (command, args) in enumerate(zip(commands, arguments), 1):
        # Distinct filenames are necessary when the same runtime directory
        # is reused after restoring an earlier GitHub memory checkpoint.
        (inbox / f"{generation:05d}_{number:02d}.json").write_text(
            json.dumps({"command": command, "args": args, "from": "github_synthetic_run"}),
            encoding="utf-8",
        )
    # Deliberately allowlist inherited environment: no tokens, keys or user data
    # are made visible to BEAN or written to the publicly committed checkpoint.
    env = {key: val for key, val in os.environ.items() if key in {
        "PATH", "HOME", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
        "LD_LIBRARY_PATH", "PYTHONPATH", "VIRTUAL_ENV", "PYTHONIOENCODING",
    }}
    env.update({
        "BEAN_DB_PATH": str(core.resolve()),
        "BEAN_INBOX_DIR": str(inbox.resolve()),
        "BEAN_REASONING_LESSONS_DB": str(reasoning.resolve()),
        "BEAN_REASONING_ENABLED": "1",
        "BEAN_REASONING_PROVIDER": "",  # No cloud or mock LLM inference.
        "BEAN_ALLOW_WEB_GOAL_RESEARCH": "0",
        "BEAN_TASK_CONFIG": "",
        "BEAN_WATCH_CONFIG": "",
    })
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bean_run.py"), "--no-seed",
         "--ticks", str(ticks), "--hz", str(hz), "--db", str(core.resolve())],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=150,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("BEAN Core invocation failed: " + result.stderr[-3500:])
    failed = list((inbox / "failed").glob("*.json"))
    if failed or len(list((inbox / "processed").glob("*.json"))) != previously_processed + len(commands):
        raise RuntimeError("BEAN did not process both digital cognition commands")
    boots, events, _, processed = sqlite_stats(core)
    if processed < len(commands) or (prior and (boots != prior["boots"] + 1 or
                                                  events <= prior["events"])):
        raise RuntimeError("BEAN failed verified restart or event continuity")
    if not prior and boots != 1:
        raise RuntimeError("fresh synthetic BEAN boot was not fresh")
    receipt = checkpoint(state_dir, runtime_dir, prior, boots, events, processed, ticks)
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke BEAN Core with GitHub-persisted synthetic memory")
    parser.add_argument("--state-dir", type=Path, default=Path("research/github_brain"))
    parser.add_argument("--runtime-dir", type=Path, default=Path(".bean-github-runtime"))
    parser.add_argument("--ticks", type=int, default=12)
    parser.add_argument("--hz", type=int, default=20)
    args = parser.parse_args()
    invoke(args.state_dir, args.runtime_dir, args.ticks, args.hz)


if __name__ == "__main__":
    main()
