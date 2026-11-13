#!/usr/bin/env python3
"""Produce labeled reproducible fixture art using BEAN's actual Python Core.

NOT a live model-selected drawing: scripted responses exercise the existing
SketchLab code, real SQLite journal, SVG renderer and sidecar preservation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bean.creativity.sketch_lab import SketchLab
from bean.learning import NativeReasoningService


class FixtureModel:
    model_id = "scripted-rocket-fixture"
    provider_kind = "synthetic_fixture"

    def __init__(self) -> None:
        self.replies = [
            {"subject": "A little rocket", "reference_query": ""},
            {"description": "Simple rocket with window, body and nose",
             "shapes": [
                 {"type": "polyline", "points": [[108, 169], [108, 85], [128, 49],
                                                [148, 85], [148, 169]]},
                 {"type": "line", "x1": 108, "y1": 169, "x2": 148, "y2": 169},
                 {"type": "circle", "cx": 128, "cy": 104, "r": 12}
             ]},
            {"claimed_subject": "rocket", "satisfied": False,
             "changes": "Add two fins and a flame."},
            {"description": "Rocket with nose, porthole, twin fins and flame",
             "shapes": [
                 {"type": "polyline", "points": [[108, 172], [108, 85], [128, 49],
                                                [148, 85], [148, 172], [108, 172]]},
                 {"type": "circle", "cx": 128, "cy": 105, "r": 12},
                 {"type": "polyline", "points": [[108, 140], [91, 174], [108, 167]]},
                 {"type": "polyline", "points": [[148, 140], [165, 174], [148, 167]]},
                 {"type": "polyline", "points": [[118, 172], [128, 211], [138, 172]]},
                 {"type": "line", "x1": 115, "y1": 135, "x2": 141, "y2": 135},
             ]},
            {"claimed_subject": "rocket", "satisfied": True,
             "changes": "No further changes in this scripted test."}
        ]

    def complete(self, query, context):
        if not self.replies:
            raise RuntimeError("Unexpected extra model call in fixture")
        return json.dumps(self.replies.pop(0))


def make_demo(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bean-draw-core-") as temp:
        core = NativeReasoningService(Path(temp) / "journal.sqlite3",
                                      model=FixtureModel())
        try:
            result = SketchLab(core).run(
                task_ref="synthetic-rocket-gallery-fixture",
                output_dir=out, backend="stdlib", max_attempts=2)
            if len(result["history"]) != 2 or not all(
                    row["sha256"] for row in result["history"]):
                raise AssertionError("Expected two rendered fixture SVG attempts")
            if not all(Path(row["metadata"]).is_file()
                       for row in result["history"]):
                raise AssertionError("Core sidecar metadata was not preserved")
            return result
        finally:
            core.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = make_demo(args.out)
    print(json.dumps(result, sort_keys=True, indent=2))
