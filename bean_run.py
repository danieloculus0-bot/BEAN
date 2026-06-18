#!/usr/bin/env python3
"""
Start BEAN's runtime loop on the Jetson.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bean.runtime.bootstrap import start_bean, shutdown_bean
from bean.body.config_loader import load_registry
from bean.body.state import BodyState
from bean.motion.safety import MotionSafety
from bean.motion.simulator import MotionSimulator
from bean.motion.skills import SkillLibrary, seed_initial_skills
from bean.motion.teaching import TeachingLayer
from bean.runtime.monitor import SystemMonitor
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import register_all
from bean.runtime.tick_handlers import build_default_handlers
from bean.runtime.loop import BeanLoop
from bean.memory.event_logger import log_event, EventType, Source


def main() -> int:
    parser = argparse.ArgumentParser(description="Start BEAN runtime loop.")
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--hz", type=float, default=float(os.environ.get("BEAN_TICK_HZ", "1.0")))
    parser.add_argument("--db", type=str, default=os.environ.get("BEAN_DB_PATH"))
    parser.add_argument("--inbox", type=str, default=os.environ.get("BEAN_INBOX_DIR", "bean/runtime/inbox_drop"))
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()

    ctx = start_bean(db_path=args.db)
    session_uuid = ctx["session_uuid"]
    loop = None
    try:
        registry = load_registry()
        body_state = BodyState(registry=registry)
        safety = MotionSafety(registry=registry)
        simulator = MotionSimulator(body_state=body_state)
        library = SkillLibrary()
        teaching = TeachingLayer(safety=safety, simulator=simulator, library=library, body_state=body_state)
        if not args.no_seed:
            result = seed_initial_skills(library)
            if result.get("seeded"):
                log_event(session_uuid, EventType.CAPABILITY_CHANGE, f"Seeded initial skills: {result['seeded']}", Source.SYSTEM, data=result)

        monitor = SystemMonitor()
        inbox = CommandInbox(args.inbox)
        handlers = build_default_handlers(monitor=monitor, inbox=inbox, monitor_interval=10, reflection_interval=300, inbox_interval=1)
        loop = BeanLoop(ctx, handlers, tick_rate_hz=args.hz, max_ticks=args.ticks)
        register_all(inbox, loop=loop, teaching_layer=teaching, monitor=monitor, ctx=ctx)

        def _signal_shutdown(signum, frame):
            loop.request_shutdown(reason=f"signal_{signum}")
        signal.signal(signal.SIGINT, _signal_shutdown)
        signal.signal(signal.SIGTERM, _signal_shutdown)

        print(f"BEAN runtime started. session={session_uuid} inbox={Path(args.inbox).resolve()}")
        loop.run()
        return 0
    finally:
        shutdown_bean(reason="runtime_exit")


if __name__ == "__main__":
    raise SystemExit(main())
