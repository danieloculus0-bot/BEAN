"""Boot readiness checks for BEAN OS rebuilds.

This module verifies that the brain stack can import, initialize SQLite schemas,
open a session, run tiny no-motion probes, and shut down cleanly.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def _reset_store_threadlocal():
    try:
        from ..memory.store import _local
        if hasattr(_local, "conn") and _local.conn:
            _local.conn.close()
            _local.conn = None
    except Exception:
        pass


def _count(table: str) -> int:
    from ..memory.store import get_store
    try:
        row = get_store().fetchone(f"SELECT COUNT(*) AS n FROM {table}")
        return int(row["n"] if row else 0)
    except Exception:
        return 0


def run_boot_readiness_check(db_path: str | None = None, *, use_temp_db: bool = False) -> dict:
    """Run a no-motion boot check and return a structured report."""
    _reset_store_threadlocal()
    if use_temp_db or not db_path:
        tmpdir = tempfile.mkdtemp(prefix="bean_boot_check_")
        resolved_db = str(Path(tmpdir) / "boot_readiness.db")
    else:
        resolved_db = db_path

    report = {
        "success": True,
        "db_path": resolved_db,
        "motion_enabled": False,
        "checks": {},
        "errors": [],
    }

    try:
        from ..memory.store import init_store
        from ..memory.identity import bootstrap_identity
        from ..memory.session import begin_session, end_session
        from ..memory.event_logger import log_event, EventType, Source

        init_store(resolved_db)
        bootstrap_identity()
        session_uuid = begin_session()
        report["session_uuid"] = session_uuid
        report["checks"]["core_memory"] = True

        event_id = log_event(session_uuid, EventType.OBSERVATION, "Boot readiness heartbeat.", Source.SYSTEM, subtype="boot_readiness")
        report["checks"]["event_log"] = event_id > 0

        from ..relationship.relationship_store import RelationshipStore
        RelationshipStore()
        report["checks"]["relationship_schema"] = True

        from ..wisdom.activation_engine import WisdomActivationEngine
        wisdom = WisdomActivationEngine().process_event(session_uuid, "Future plan changed and remains uncertain.", event_id, {"stated_reason": "capacity"})
        report["checks"]["wisdom_probe"] = bool(wisdom.get("trace_id"))

        from ..reasoning.reasoning_engine import ReasoningEngine
        reasoning = ReasoningEngine().run(session_uuid, adapter_name="mock")
        report["checks"]["reasoning_probe"] = bool(reasoning.get("proposal_id")) and reasoning.get("motion_command_generated") is False

        from ..speculation import init_speculation
        speculation = init_speculation().create_hypothesis(session_uuid, "This might need follow-up after boot.", claim_type="hypothesis", evidence_level="hypothetical")
        report["checks"]["hypothesis_probe"] = bool(speculation.get("hypothesis_id"))

        from .proof import RuntimeProof
        proof = RuntimeProof().run(session_uuid)
        report["checks"]["runtime_proof"] = proof.get("motion_enabled") is False

        report["counts"] = {
            "events": _count("events"),
            "wisdom_activation_traces": _count("wisdom_activation_traces"),
            "reasoning_proposals": _count("reasoning_proposals"),
            "speculative_hypotheses": _count("speculative_hypotheses"),
            "supervisor_relationships": _count("supervisor_relationships"),
        }
        end_session(session_uuid, reason="boot_readiness_complete", notes="Boot readiness check complete.")
    except Exception as exc:
        import traceback
        report["success"] = False
        report["errors"].append(str(exc))
        report["traceback"] = traceback.format_exc()

    report["success"] = report["success"] and all(report["checks"].values()) if report["checks"] else False
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BEAN boot readiness checks.")
    parser.add_argument("--db", default=os.environ.get("BEAN_DB_PATH"), help="SQLite DB path. Defaults to BEAN_DB_PATH or temp DB.")
    parser.add_argument("--temp", action="store_true", help="Use a temporary DB even if BEAN_DB_PATH is set.")
    args = parser.parse_args()
    report = run_boot_readiness_check(args.db, use_temp_db=args.temp or not args.db)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
