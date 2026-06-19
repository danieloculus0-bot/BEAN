#!/usr/bin/env python3
"""
bean_run.py

Start BEAN. This is the entry point for the Jetson.
"""

import argparse
import os
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
from bean.world.model_store import ModelStore
from bean.world.self_model import SelfModel
from bean.world.world_model import WorldModel
from bean.world.updater import ModelUpdater
from bean.runtime.monitor import SystemMonitor
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import register_all
from bean.runtime.tick_handlers import build_default_handlers
from bean.runtime.loop import BeanLoop
from bean.memory.event_logger import log_event, EventType, Source


def main():
    parser = argparse.ArgumentParser(description="Start BEAN runtime loop.")
    parser.add_argument("--ticks", type=int, default=None, help="Stop after N ticks")
    parser.add_argument("--hz", type=float, default=1.0, help="Tick rate in Hz")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite memory DB")
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding initial skills")
    args = parser.parse_args()

    tick_rate = float(os.environ.get("BEAN_TICK_HZ", args.hz))
    db_path = os.environ.get("BEAN_DB_PATH", args.db)
    inbox_dir = os.environ.get("BEAN_INBOX_DIR", None)

    ctx = start_bean(db_path=db_path)
    session_uuid = ctx["session_uuid"]

    try:
        registry = load_registry()
        body_state = BodyState(registry=registry)
        safety = MotionSafety(registry=registry)
        simulator = MotionSimulator(body_state=body_state)
        library = SkillLibrary()
        teaching = TeachingLayer(safety, simulator, library, body_state)

        if not args.no_seed:
            result = seed_initial_skills(library)
            if result.get("seeded"):
                log_event(session_uuid, EventType.CAPABILITY_CHANGE, f"Seeded initial skills: {result['seeded']}", Source.SYSTEM, data=result)

        body_state.write_to_memory(session_uuid)

        model_store = ModelStore()
        self_model = SelfModel(store=model_store)
        world_model = WorldModel(store=model_store)
        model_updater = ModelUpdater(self_model, world_model, model_store)
        model_updater.run(session_uuid, trigger="session_start")

        monitor = SystemMonitor()
        inbox = CommandInbox(inbox_dir=inbox_dir) if inbox_dir else CommandInbox()
        handlers = build_default_handlers(monitor, inbox, teaching, model_updater=model_updater)
        loop = BeanLoop(ctx, handlers, tick_rate_hz=tick_rate, max_ticks=args.ticks)
        register_all(inbox, loop, teaching, monitor, ctx, model_updater=model_updater)
        loop.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        log_event(session_uuid, EventType.ERROR, f"Unhandled exception in bean_run.py: {e}", Source.SYSTEM, data={"traceback": traceback.format_exc()})
        raise
    finally:
        shutdown_bean(ctx, reason="clean")


if __name__ == "__main__":
    main()
