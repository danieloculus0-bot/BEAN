"""Independent post-selection transfer audit for BEAN's native transfer gate.

A paired probe can select a policy, but cannot certify held-out transfer.
This module runs disjoint task IDs against frozen named candidates and emits
a content-addressed receipt. The evaluator is caller-provided; provenance of
its labels is not independently authenticated.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from .transfer_gate import SCHEMA, evaluate_transfer

AUDIT_SCHEMA = "bean.native.transfer_holdout.v1"


def audit_transfer(*, selection, holdout_ids, reward, controls,
                   minimum_advantage=0.0):
    """Evaluate the frozen selected policy on unseen IDs against all controls.

    controls must name frozen, no-memory, grammar-matched and strong agents.
    All candidates get exactly one reward call per held-out ID, in a fixed
    order. No adaptation, policy selection or model calls occur in this audit.
    """
    if not isinstance(selection, dict) or selection.get("schema") != SCHEMA:
        raise ValueError("A native transfer selection receipt is required")
    digest = selection.get("evidence_sha256")
    payload = {k: v for k, v in selection.items() if k != "evidence_sha256"}
    expected = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                allow_nan=False).encode()).hexdigest()
    if digest != expected:
        raise ValueError("Selection receipt integrity failure")
    chosen = selection.get("selected")
    if chosen is None:
        raise ValueError("Inconclusive selection cannot be promoted")
    if not isinstance(holdout_ids, (list, tuple)) or not 2 <= len(holdout_ids) <= 100:
        raise ValueError("Require 2..100 held-out task IDs")
    if any(not isinstance(x, str) or not x.strip() or len(x) > 128
           for x in holdout_ids) or len(set(holdout_ids)) != len(holdout_ids):
        raise ValueError("Held-out IDs must be unique bounded strings")
    probe_ids = {row["probe_id"] for row in selection["pairs"]}
    if probe_ids.intersection(holdout_ids):
        raise ValueError("Held-out tasks overlap selection probes")
    required = ("frozen", "no_memory", "grammar_matched", "strong")
    if not isinstance(controls, dict) or set(controls) != set(required):
        raise ValueError("Four named matched-budget controls required")
    candidates = [chosen] + [controls[k] for k in required]
    if any(not isinstance(x, str) or not x.strip() for x in candidates):
        raise ValueError("Candidate identifiers must be nonempty")
    if len(set(candidates)) != len(candidates):
        raise ValueError("Candidate identifiers must be distinct")
    if not callable(reward):
        raise ValueError("An executable reward evaluator is required")
    if type(minimum_advantage) not in (int, float) or not math.isfinite(minimum_advantage) or minimum_advantage < 0:
        raise ValueError("Invalid advantage threshold")
    rows = []
    for task in holdout_ids:
        scores = {}
        for name in candidates:
            value = reward(name, task)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Evaluator must return finite numeric scores")
            scores[name] = float(value)
        rows.append({"task_id": task, "scores": scores})
    means = {name: sum(row["scores"][name] for row in rows) / len(rows)
             for name in candidates}
    margins = {key: means[chosen] - means[controls[key]] for key in required}
    record = {
        "schema": AUDIT_SCHEMA, "selection_sha256": digest,
        "selected": chosen, "controls": controls, "cases": rows,
        "task_count": len(rows), "calls_per_candidate": len(rows),
        "means": means, "advantages": margins,
        "minimum_advantage": float(minimum_advantage),
        "passed": all(value > minimum_advantage for value in margins.values()),
        "independent_evaluator_attested": False,
        "provider": "caller_supplied_not_verified",
        "scope": "post_selection_disjoint_ids_only",
    }
    record["evidence_sha256"] = sha256(json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()
    return record
