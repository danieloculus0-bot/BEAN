#!/usr/bin/env python3
"""Offline demonstration of BEAN's host-neutral, proposal-only reasoning path.

No hosted model, network call, ERP credentials, robot or persistent user data.
The database is temporary; the mock provider does not demonstrate intelligence.
Run from the repository root: python -m examples.quickstart_reasoning
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bean.integration import BeanReasoningLayer


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="bean-public-demo-") as directory:
        db_file = Path(directory) / "demo.sqlite3"
        with BeanReasoningLayer(str(db_file)) as bean:
            result = bean.observe_and_reason(
                "A sample sensor report arrived with an unverified measurement.",
                data={
                    "host": "synthetic_demo",
                    "source_id": "fixture-001",
                    "measurement": None,
                    "verified": False,
                },
                adapter_name="mock",
            )
            fields = (
                "event_id",
                "proposal_id",
                "requires_supervisor_review",
                "motion_command_generated",
                "memory_written",
            )
            print(json.dumps({field: result.get(field) for field in fields}, indent=2))
            if not result.get("proposal_id"):
                raise RuntimeError("BEAN did not persist a proposal")
            if result.get("requires_supervisor_review") is not True:
                raise RuntimeError("Review boundary was not applied")
            if result.get("motion_command_generated") is not False:
                raise RuntimeError("Unexpected motion command in a read-only demo")

    print("Offline mock demonstration complete; temporary data cleaned up.")


if __name__ == "__main__":
    main()
