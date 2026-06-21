"""BEAN Brain 0.2 install smoke test.

This test proves the no-motion brain stack can initialize, tick, update models,
run consolidation, run coherence, and process inbox commands against a temporary
SQLite memory database.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session, end_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.world.model_store import ModelStore
from bean.world.self_model import SelfModel
from bean.world.world_model import WorldModel
from bean.world.updater import ModelUpdater
from bean.cognition.significance import SignificanceScorer
from bean.cognition.significance_weights import SignificanceWeightManager
from bean.cognition.surprise import SurpriseDetector
from bean.cognition.preference import PreferenceEngine
from bean.cognition.drive import DriveEvaluator
from bean.cognition.goal_state import GoalStateEngine
from bean.cognition.consolidation import ConsolidationEngine
from bean.cognition.state_collapse import StateCollapseManager
from bean.cognition.coherence import CoherenceEngine
from bean.cognition.entropy import EntropySource
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import register_all
from bean.runtime.tick_handlers import build_default_handlers
from bean.runtime.loop import BeanLoop


def make_temp_brain():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    db_path = tmpdir / "bean_brain_install_test.db"
    inbox_dir = tmpdir / "inbox"
    init_store(str(db_path))
    bootstrap_identity()
    session_uuid = begin_session()
    return tmpdir, db_path, inbox_dir, session_uuid


def build_brain_stack(session_uuid: str, inbox_dir: Path):
    model_store = ModelStore()
    self_model = SelfModel(store=model_store)
    world_model = WorldModel(store=model_store)
    model_updater = ModelUpdater(self_model, world_model, model_store)

    weights = SignificanceWeightManager().load_or_create()
    scorer = SignificanceScorer(
        type_scores=weights.event_type_weights,
        severity_modifiers=weights.severity_modifiers,
        subtype_modifiers=weights.subtype_modifiers,
    )

    state_manager = StateCollapseManager()
    state_manager.seed_initial_states()
    entropy = EntropySource()
    entropy.seed_from_event_log(session_uuid)

    consolidation = ConsolidationEngine(
        scorer=scorer,
        surprise_detector=SurpriseDetector(model_store=model_store),
        preference_engine=PreferenceEngine(),
        drive_evaluator=DriveEvaluator(),
        goal_engine=GoalStateEngine(),
        model_updater=model_updater,
    )
    coherence = CoherenceEngine(state_manager=state_manager, entropy=entropy)
    inbox = CommandInbox(inbox_dir=inbox_dir)
    ctx = {"session_uuid": session_uuid, "_shutdown_called": False}
    handlers = build_default_handlers(
        monitor=None,
        inbox=inbox,
        teaching_layer=None,
        model_updater=model_updater,
        consolidation_engine=consolidation,
        coherence_engine=coherence,
        monitor_interval=1000,
        model_update_interval=2,
        coherence_interval=2,
        consolidation_interval=3,
        reflection_interval=1000,
    )
    loop = BeanLoop(ctx, handlers, tick_rate_hz=100.0, max_ticks=3)
    register_all(
        inbox,
        loop,
        teaching_layer=None,
        monitor=None,
        ctx=ctx,
        model_updater=model_updater,
        consolidation_engine=consolidation,
        coherence_engine=coherence,
        state_manager=state_manager,
    )
    return model_updater, state_manager, consolidation, coherence, inbox, loop, ctx


def test_brain_install_stack_runs():
    _, _, inbox_dir, session_uuid = make_temp_brain()
    model_updater, state_manager, consolidation, coherence, inbox, loop, ctx = build_brain_stack(session_uuid, inbox_dir)

    log_event(session_uuid, EventType.SENSOR_READING, "Camera heartbeat observed during smoke test.", Source.SENSOR, subtype="camera_heartbeat")
    model_update = model_updater.run(session_uuid, trigger="smoke_test")
    assert model_update["total_active_claims"] > 0

    coherence_report = coherence.run(session_uuid, trigger="smoke_test")
    assert coherence_report.states_reviewed >= 4

    consolidation_report = consolidation.run(session_uuid, trigger="smoke_test")
    assert consolidation_report.events_reviewed >= 0

    inbox.drop("status", sender="smoke_test")
    inbox.drop("run_coherence", {"trigger": "inbox_smoke"}, sender="smoke_test")
    inbox.drop("run_consolidation", {"trigger": "inbox_smoke"}, sender="smoke_test")
    loop.run()

    assert get_store().fetchone("SELECT COUNT(*) AS n FROM world_claims WHERE active=1")["n"] > 0
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM cognition_possibility_states WHERE active=1")["n"] >= 4
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM cognition_consolidations")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM cognition_coherence_windows")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events WHERE subtype='inbox_command_processed'")["n"] >= 3

    end_session(session_uuid, reason="clean", notes="Brain install smoke test complete.")


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    passed = failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
            passed += 1
        except Exception:
            print(f"FAIL {name}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
