#!/usr/bin/env python3
"""Safe BEAN runtime placeholder for BEAN OS v0.

This is intentionally brain-only. It initializes the persistent data paths,
boots the memory store, writes heartbeat/status files, and processes the file
inbox if available. It does not enable physical motion.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNNING = True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def handle_stop(signum, frame) -> None:  # noqa: ARG001
    global RUNNING
    RUNNING = False


def env_path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default)).expanduser()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def init_memory(db_path: Path) -> dict:
    try:
        from bean.memory.store import init_store, get_store
        init_store(str(db_path))
        store = get_store()
        return {"ok": True, "db_path": str(db_path), "store": str(type(store).__name__)}
    except Exception as exc:  # runtime should stay visible even if memory init fails
        return {"ok": False, "db_path": str(db_path), "error": str(exc)}


def runtime_loop() -> int:
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    data_dir = env_path("BEAN_DATA", "/var/lib/bean")
    log_dir = env_path("BEAN_LOG_DIR", "/var/log/bean")
    db_path = env_path("BEAN_DB_PATH", str(data_dir / "bean_memory.db"))
    inbox_dir = env_path("BEAN_INBOX_DIR", str(data_dir / "inbox"))
    heartbeat_path = data_dir / "heartbeat.json"
    status_path = data_dir / "status.json"
    log_path = log_dir / "bean_safe_runtime.log"

    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir.mkdir(parents=True, exist_ok=True)

    memory_status = init_memory(db_path)
    startup = {
        "timestamp": utc_now(),
        "runtime": "bean_safe_runtime",
        "runtime_mode": os.getenv("BEAN_RUNTIME_MODE", "safe"),
        "motion_enabled": False,
        "sentience_claimed": False,
        "inbox_dir": str(inbox_dir),
        "memory": memory_status,
    }
    write_json(status_path, startup)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(json.dumps({"event": "startup", **startup}) + "\n")

    tick = 0
    while RUNNING:
        tick += 1
        heartbeat = {
            "timestamp": utc_now(),
            "tick": tick,
            "runtime": "bean_safe_runtime",
            "motion_enabled": False,
            "sentience_claimed": False,
            "status": "running",
        }
        write_json(heartbeat_path, heartbeat)
        if tick % 12 == 0:
            with log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"event": "heartbeat", **heartbeat}) + "\n")
        time.sleep(5)

    shutdown = {
        "timestamp": utc_now(),
        "runtime": "bean_safe_runtime",
        "motion_enabled": False,
        "sentience_claimed": False,
        "status": "stopped",
    }
    write_json(status_path, shutdown)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(json.dumps({"event": "shutdown", **shutdown}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(runtime_loop())
