"""
bean/runtime/inbox.py

File-based command inbox for the BEAN runtime loop.
A supervisor can drop JSON files into the inbox directory from another terminal.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ..memory.event_logger import log_event, EventType, Source, Severity

MAX_INBOX_BYTES = 64 * 1024


def _safe_metadata(args):
    """Log request shape rather than secrets, model prompts or source documents."""
    if not isinstance(args, dict):
        return {"arguments_valid": False}
    return {"argument_keys": sorted(str(x)[:80] for x in args)[:40],
            "argument_count": len(args)}



def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InboxMessage:
    command: str
    args: dict = field(default_factory=dict)
    sender: str = "unknown"
    path: Optional[Path] = None
    received_at: str = field(default_factory=_now)


class CommandInbox:
    def __init__(self, inbox_dir: str | Path = "bean/runtime/inbox_drop"):
        self.inbox_dir = Path(inbox_dir)
        self.processed_dir = self.inbox_dir / "processed"
        self.failed_dir = self.inbox_dir / "failed"
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        self.failed_dir.mkdir(exist_ok=True)
        self._handlers: dict[str, Callable[[InboxMessage, str], dict]] = {}

    def register(self, command: str, handler: Callable[[InboxMessage, str], dict]):
        self._handlers[command] = handler

    def drop(self, command: str, args: Optional[dict] = None, sender: str = "supervisor") -> Path:
        if not isinstance(command, str) or not 1 <= len(command) <= 128 or not command.strip():
            raise ValueError("A bounded command name is required")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            raise ValueError("Command arguments must be an object")
        payload = json.dumps({"command": command, "args": args, "from": sender},
                             separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(payload) > MAX_INBOX_BYTES:
            raise ValueError("Command exceeds bounded inbox request size")
        stem = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}_{uuid.uuid4().hex}"
        path = self.inbox_dir / (stem + ".json")
        staging = self.inbox_dir / (stem + ".tmp")
        try:
            with staging.open("xb") as handle:
                handle.write(payload)
            # Pollers never see an unfinished JSON request.
            os.replace(staging, path)
        finally:
            staging.unlink(missing_ok=True)
        return path

    def poll(self, session_uuid: str) -> list[dict]:
        results: list[dict] = []
        for path in sorted(self.inbox_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
            results.append(self._process_one(path, session_uuid))
        return results

    def _process_one(self, path: Path, session_uuid: str) -> dict:
        try:
            if path.stat().st_size > MAX_INBOX_BYTES:
                raise ValueError("Inbox command exceeds maximum size")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Inbox command must be a JSON object")
        except (OSError, ValueError, UnicodeError) as e:
            log_event(session_uuid, EventType.ERROR, f"Inbox parse error for {path.name}: {e}", Source.SYSTEM, subtype="inbox_parse_error", severity=Severity.ERROR, data={"path": str(path), "error": str(e)})
            self._move(path, self.failed_dir)
            return {"status": "parse_error", "path": str(path), "error": str(e)}

        command = raw.get("command")
        if not isinstance(command, str) or not command.strip() or len(command) > 128:
            log_event(session_uuid, EventType.WARNING, f"Inbox file has no command: {path.name}", Source.SYSTEM, subtype="inbox_no_command", severity=Severity.WARN, data=raw)
            self._move(path, self.failed_dir)
            return {"status": "no_command", "path": str(path)}

        if not isinstance(raw.get("args", {}), dict):
            log_event(session_uuid, EventType.WARNING, "Inbox arguments are not an object.", Source.SYSTEM, subtype="inbox_bad_args", data={"command": command})
            self._move(path, self.failed_dir)
            return {"status": "invalid_args", "command": command, "path": str(path)}
        msg = InboxMessage(command=command, args=raw.get("args", {}), sender=raw.get("from") or raw.get("sender") or "unknown", path=path)
        log_event(session_uuid, EventType.HUMAN_COMMAND, f"Inbox command received: {msg.command}", Source.HUMAN, subtype="inbox_command_received", data={"command": msg.command, **_safe_metadata(msg.args)})

        handler = self._handlers.get(msg.command)
        if handler is None:
            log_event(session_uuid, EventType.WARNING, f"Unknown inbox command: {msg.command}", Source.SYSTEM, subtype="inbox_unknown_command", severity=Severity.WARN, data={"command": msg.command, **_safe_metadata(msg.args)})
            self._move(path, self.failed_dir)
            return {"status": "unknown_command", "command": msg.command, "path": str(path)}

        try:
            result = handler(msg, session_uuid) or {}
        except Exception as e:
            log_event(session_uuid, EventType.ERROR, f"Inbox handler error for {msg.command}: {type(e).__name__}", Source.SYSTEM, subtype="inbox_handler_error", severity=Severity.ERROR, data={"command": msg.command, "exception_class": type(e).__name__})
            self._move(path, self.failed_dir)
            return {"status": "handler_error", "command": msg.command, "exception_class": type(e).__name__, "path": str(path)}

        log_event(session_uuid, EventType.HUMAN_COMMAND, f"Inbox command processed: {msg.command}", Source.SYSTEM, subtype="inbox_command_processed", data={"command": msg.command, "result_type": type(result).__name__})
        self._move(path, self.processed_dir)
        return {"status": "ok", "command": msg.command, "result": result, "path": str(path)}

    def _move(self, path: Path, dest_dir: Path):
        if path.exists():
            shutil.move(str(path), str(dest_dir / path.name))
