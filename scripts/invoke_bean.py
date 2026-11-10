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
# Direct CLI invocation adds scripts/ rather than repository root to sys.path.
# Restore native BEAN package imports for GitHub Issue workflow runs.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
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
        if any(any(state_dir.glob(compressed + "*")) for compressed, _ in CHECKPOINTS.values()):
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
        archive_ref = record.get("archive", archive)
        if not isinstance(archive_ref, str) or (archive_ref != archive and
                not re.fullmatch(re.escape(archive) + r"\.g[0-9]{5,}", archive_ref)):
            raise ValueError("invalid BEAN generation archive reference")
        compressed = state_dir / archive_ref
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
    generation = prior["generation"] + 1 if prior else 1
    for name, (archive, filename) in CHECKPOINTS.items():
        path = runtime_dir / filename
        check_sqlite(path)
        # SQLite's backup API writes a consistent copy, never a live WAL stream.
        backup = runtime_dir / (filename + ".backup")
        # sqlite3.Connection context managers do not CLOSE connections.
        # Close both before unlinking the temporary backup (required on Windows).
        from contextlib import closing
        with closing(sqlite3.connect(str(path))) as source:
            with closing(sqlite3.connect(str(backup))) as target:
                source.backup(target)
        payload = backup.read_bytes()
        if len(payload) > MAX_UNCOMPRESSED:
            raise ValueError("BEAN memory exceeded public checkpoint size limit")
        compressed = gzip.compress(payload, mtime=0)
        if len(compressed) > MAX_COMPRESSED:
            raise ValueError("BEAN memory exceeded compressed checkpoint size limit")
        # Immutable generation archives keep the previous manifest restorable
        # if any later archive write or manifest publication fails.
        versioned = f"{archive}.g{generation:05d}"
        destination = state_dir / versioned
        if destination.exists():
            # Preserve immutable evidence after a partial prior publication.
            # Only an identical retry may reuse an orphaned archive.
            if destination.read_bytes() != compressed:
                raise ValueError("BEAN generation archive conflicts with retry")
        else:
            staging_archive = state_dir / (versioned + ".tmp")
            staging_archive.write_bytes(compressed)
            staging_archive.replace(destination)
        databases[name] = {"sha256": digest(payload), "bytes": len(payload), "archive": versioned}
        backup.unlink()
    source_sha = os.environ.get("GITHUB_SHA", "local-validation")
    if not (source_sha == "local-validation" or re.fullmatch(r"[0-9a-f]{40}", source_sha)):
        raise ValueError("invalid source revision")
    receipt = {
        "schema": "bean.github.invoke.v1",
        "synthetic_only": True,
        "generation": generation,
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



def serve_public_request(reasoning_db: Path, request: dict) -> dict:
    """Use BEAN's existing native reasoning service; no model or outside effects.

    This is deliberately narrower than Core's full inbox. The caller may ask
    for status, evidence-backed recall or bounded local symbolic reasoning.
    """
    if (not isinstance(request, dict)
            or set(request) != {"schema", "command", "args"}
            or request["schema"] != "bean.github.request.v1"):
        raise ValueError("Invalid public BEAN request envelope")
    command, args = request["command"], request["args"]
    if command not in {"reasoning_status", "reasoning_recall", "reasoning_local"}:
        raise ValueError("Unsupported public BEAN command")
    if not isinstance(args, dict):
        raise ValueError("BEAN request args must be an object")
    from bean.learning.reasoning_service import NativeReasoningService
    service = NativeReasoningService(reasoning_db, model=None)
    try:
        if command == "reasoning_status":
            if args:
                raise ValueError("reasoning_status takes no arguments")
            return service.status()
        if command == "reasoning_recall":
            if set(args) != {"domain", "query", "limit"}:
                raise ValueError("reasoning_recall requires domain, query, limit")
            return service.recall(**args)
        if set(args) != {"domain", "task_ref", "query"}:
            raise ValueError("reasoning_local requires domain, task_ref, query")
        return service.reason_local(**args)
    finally:
        service.close()


def prepare_public_reply(request: dict, response: dict, generation: int,
                         source_sha: str, receipt_sha256: str) -> str:
    """Validate the exact public JSON size before checkpoint publication."""
    payload = {
        "schema": "bean.github.reply.v1",
        "command": request["command"],
        "response": response,
        "generation": generation,
        "receipt_sha256": receipt_sha256,
        "source_sha": source_sha,
        "engine": "native_python_core",
        "external_model_invoked": False,
        "private_jetson_connected": False,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode("utf-8")) > 14000:
        raise ValueError("BEAN response exceeds public limit")
    return encoded


def invoke(state_dir: Path, runtime_dir: Path, ticks: int = 12, hz: int = 20,
           request: dict | None = None, reply_path: Path | None = None) -> dict:
    if not 2 <= ticks <= 120 or not 1 <= hz <= 30:
        raise ValueError("ticks must be 2..120 and hz 1..30")
    # Reject missing reply wiring before any Core state restoration or mutation.
    if request is not None and reply_path is None:
        raise ValueError("Public BEAN request needs a reply destination")
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
    reply_result = serve_public_request(reasoning, request) if request is not None else None
    if request is not None:
        # The receipt digest is a fixed-width SHA256. Substituting the real
        # digest after checkpointing cannot change the encoded reply size.
        source_sha = os.environ.get("GITHUB_SHA", "local-validation")
        if not (source_sha == "local-validation" or re.fullmatch(r"[0-9a-f]{40}", source_sha)):
            raise ValueError("invalid source revision")
        prepare_public_reply(request, reply_result, generation, source_sha, "0" * 64)
    receipt = checkpoint(state_dir, runtime_dir, prior, boots, events, processed, ticks)
    if request is not None:
        if reply_path is None:
            raise ValueError("Public BEAN request needs a reply destination")
        encoded = prepare_public_reply(request, reply_result, receipt["generation"],
                                       receipt["source_sha"], receipt["receipt_sha256"])
        reply_path.parent.mkdir(parents=True, exist_ok=True)
        reply_path.write_text(encoded + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke BEAN Core with GitHub-persisted synthetic memory")
    parser.add_argument("--state-dir", type=Path, default=Path("research/github_brain"))
    parser.add_argument("--runtime-dir", type=Path, default=Path(".bean-github-runtime"))
    parser.add_argument("--ticks", type=int, default=12)
    parser.add_argument("--hz", type=int, default=20)
    parser.add_argument("--request-file", type=Path)
    parser.add_argument("--reply-file", type=Path)
    args = parser.parse_args()
    if bool(args.request_file) != bool(args.reply_file):
        parser.error("--request-file and --reply-file must be provided together")
    request = json.loads(args.request_file.read_text(encoding="utf-8")) if args.request_file else None
    invoke(args.state_dir, args.runtime_dir, args.ticks, args.hz,
           request=request, reply_path=args.reply_file)


if __name__ == "__main__":
    main()
