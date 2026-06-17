"""
bean/runtime/bootstrap.py

The entry point for a BEAN session.
Initializes storage, bootstraps identity, starts session, reads continuity.
Returns a runtime context dict used by everything else.

Registers clean shutdown handlers so even Ctrl-C produces an honest record.
"""

import atexit
import signal
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

from ..memory.store import init_store
from ..memory.identity import bootstrap_identity, get_identity, get_active_boundaries
from ..memory.session import begin_session, end_session, get_continuity_context
from ..memory.event_logger import log_event, EventType, Source, Severity


DEFAULT_DB_PATH = Path(__file__).parent.parent / "memory" / "bean_memory.db"

_active_ctx = None


def start_bean(db_path=None, silent=False):
    """
    Initialize and start a BEAN session.
    Returns a runtime context dict.
    """
    global _active_ctx

    resolved_db = db_path or os.environ.get("BEAN_DB_PATH", str(DEFAULT_DB_PATH))

    init_store(resolved_db)
    bootstrap_identity()
    session_uuid = begin_session()

    continuity = get_continuity_context(limit=5)
    identity = get_identity()
    boundaries = get_active_boundaries()

    ctx = {
        "session_uuid": session_uuid,
        "db_path": resolved_db,
        "identity": identity,
        "boundaries": boundaries,
        "continuity": continuity,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "_shutdown_called": False,
    }
    _active_ctx = ctx

    atexit.register(_atexit_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    if not silent:
        _print_boot_summary(ctx)

    return ctx


def shutdown_bean(ctx, reason="clean", notes=None):
    """
    Clean shutdown. Call explicitly or let atexit handle it.
    """
    if ctx.get("_shutdown_called"):
        return
    ctx["_shutdown_called"] = True
    end_session(ctx["session_uuid"], reason=reason, notes=notes)
    print(f"\n[BEAN] Session ended. reason={reason} session={ctx['session_uuid'][:8]}")


def _atexit_handler():
    global _active_ctx
    if _active_ctx and not _active_ctx.get("_shutdown_called"):
        shutdown_bean(_active_ctx, reason="process_exit",
                      notes="atexit handler — likely unclean exit")


def _signal_handler(signum, frame):
    global _active_ctx
    sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    if _active_ctx and not _active_ctx.get("_shutdown_called"):
        shutdown_bean(_active_ctx, reason="keyboard_interrupt",
                      notes=f"Caught {sig_name}")
    sys.exit(0)


def _print_boot_summary(ctx):
    c = ctx["continuity"]
    identity = ctx["identity"]
    sep = "─" * 60
    print(sep)
    print(f"  BEAN  |  {identity['developmental_stage']}  |  v{identity['version']}")
    print(sep)
    print(f"  Session : {ctx['session_uuid'][:8]}...")
    print(f"  Boot #  : {c['total_boots']}")
    print(f"  Events  : {c['total_events']} total in memory")
    print(f"  Bounds  : {len(ctx['boundaries'])} active boundary rule(s)")
    recent = c["recent_sessions"]
    if len(recent) > 1:
        last = recent[1]
        last_shutdown = last.get("shutdown_reason") or "unknown"
        last_boot = last.get("boot_time", "?")[:19]
        print(f"  Last    : Boot #{last['boot_count']} at {last_boot}, ended: {last_shutdown}")
    print(sep)
