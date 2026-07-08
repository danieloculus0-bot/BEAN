"""Boot readiness checks for BEAN OS rebuilds.

This module verifies that the brain stack can import, initialize SQLite schemas,
synchronize declared identity records, open a session, run tiny no-output probes,
and shut down cleanly.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
from pathlib import Path

REQUIRED_CAPABILITIES = {
    "event_logging",
    "session_continuity",
    "relationship_trust",
    "wisdom_activation",
    "reasoning_proposals",
    "hypothesis_discipline",
    "boot_readiness_check",
}

REQUIRED_BOUNDARIES = {
    "honest_capability_reporting",
    "llm_is_tool_not_identity",
    "speculation_is_not_fact",
    "reasoning_proposals_do_not_act",
}

REQUIRED_ORIGIN_VERSION = "BEAN_ORIGIN_COVENANT_001"


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


def _names(table: str) -> set[str]:
    from ..memory.store import get_store
    try:
        return {row["name"] for row in get_store().fetchall(f"SELECT name FROM {table}")}
    except Exception:
        return set()


def _origin_present() -> bool:
    from ..memory.store import get_store
    try:
        row = get_store().fetchone("SELECT id FROM developmental_history WHERE version=?", (REQUIRED_ORIGIN_VERSION,))
        summary = get_store().fetchone("SELECT id FROM continuity_summaries WHERE summary_type='origin_covenant' LIMIT 1")
        return bool(row and summary)
    except Exception:
        return False


def _platform_report() -> dict:
    nv_tegra = Path("/etc/nv_tegra_release")
    model_path = Path("/proc/device-tree/model")
    model = ""
    if model_path.exists():
        try:
            model = model_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            model = ""
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "linux": platform.system() == "Linux",
        "arm64": platform.machine() in {"aarch64", "arm64"},
        "jetson_l4t_detected": nv_tegra.exists() or "NVIDIA" in model,
        "nv_tegra_release_present": nv_tegra.exists(),
        "device_tree_model": model.strip("\x00\n "),
    }


def run_boot_readiness_check(db_path: str | None = None, *, use_temp_db: bool = False) -> dict:
    """Run a no-output boot check and return a structured report."""
    _reset_store_threadlocal()
    if use_temp_db or not db_path:
        tmpdir = tempfile.mkdtemp(prefix="bean_boot_check_")
        resolved_db = str(Path(tmpdir) / "boot_readiness.db")
    else:
        resolved_db = db_path

    report = {
        "success": True,
        "db_path": resolved_db,
        "physical_output_enabled": False,
        "motion_enabled": False,
        "platform": _platform_report(),
        "checks": {},
        "errors": [],
    }

    try:
        from ..memory.store import init_store
        from ..memory.identity import bootstrap_identity
        from ..memory.origin import ensure_origin_records
        from ..memory.session import begin_session, end_session
        from ..memory.event_logger import EventType, Source, log_event

        init_store(resolved_db)
        bootstrap_identity()
        session_uuid = begin_session()
        report["session_uuid"] = session_uuid
        report["checks"]["core_memory"] = True

        origin = ensure_origin_records(session_uuid)
        report["checks"]["origin_covenant"] = _origin_present()
        report["origin_covenant"] = {"version": REQUIRED_ORIGIN_VERSION, "created": origin.get("created")}

        capability_names = _names("capabilities")
        boundary_names = _names("boundaries")
        missing_capabilities = sorted(REQUIRED_CAPABILITIES - capability_names)
        missing_boundaries = sorted(REQUIRED_BOUNDARIES - boundary_names)
        report["checks"]["capability_sync"] = not missing_capabilities
        report["checks"]["boundary_sync"] = not missing_boundaries
        report["missing_capabilities"] = missing_capabilities
        report["missing_boundaries"] = missing_boundaries

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
            "capabilities": _count("capabilities"),
            "boundaries": _count("boundaries"),
            "developmental_history": _count("developmental_history"),
            "continuity_summaries": _count("continuity_summaries"),
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
