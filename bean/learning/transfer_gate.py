"""BEAN CPU-only evidence gate: test an old rule before applying it elsewhere.

The host provides candidate policies and a callable that actually probes the
environment. No oracle labels, LLM calls, fixed winning policy, or privileged
target-state access exist in this decision function. It is NOT an autonomous
candidate-rule generator. The caller is responsible for independently held-out
evaluation; the gate only sees its paired probe rewards.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math


SCHEMA = "bean.native.selective_transfer.v1"


def evaluate_transfer(*, retained, alternative, probe_ids, reward,
                      margin=0.0):
    """Return auditable keep/reject decision from matched reward observations.

    reward(policy_id, probe_id) must perform a genuine evaluation and return a
    finite real-valued reward. A tie or inconclusive result rejects transfer.
    Probe IDs must be disjoint from subsequent held-out test IDs.
    """
    if not all(isinstance(p, str) and 0 < len(p.strip()) <= 128
               for p in (retained, alternative)) or retained == alternative:
        raise ValueError("Distinct named candidate policies required")
    if (not isinstance(probe_ids, (tuple, list))
            or not 1 <= len(probe_ids) <= 16
            or any(not isinstance(p, str) or not 1 <= len(p) <= 128
                   for p in probe_ids)
            or len(set(probe_ids)) != len(probe_ids)):
        raise ValueError("Require 1..16 unique paired probe IDs")
    if not callable(reward):
        raise ValueError("Actual reward evaluator required")
    if type(margin) not in (int, float) or not math.isfinite(margin) or margin < 0:
        raise ValueError("Margin must be finite and nonnegative")
    pairs = []
    for case in probe_ids:
        values = []
        for candidate in (retained, alternative):
            value = reward(candidate, case)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Finite observed rewards required")
            values.append(float(value))
        pairs.append({"probe_id": case, "retained_reward": values[0],
                      "alternative_reward": values[1],
                      "difference": values[0] - values[1]})
    delta = sum(p["difference"] for p in pairs) / len(pairs)
    keep = delta > float(margin)
    record = {
        "schema": SCHEMA, "retained": retained, "alternative": alternative,
        "pairs": pairs, "number_of_pairs": len(pairs),
        "average_advantage": delta, "required_margin": float(margin),
        "selected": retained if keep else alternative,
        "transfer_accepted": keep,
        "decision": "reuse" if keep else "reject_or_abstain",
        "measured_in": "paired_probe_reward",
        "candidate_generator": "supplied_by_host",
        "oracle_labels_used": False,
        "heldout_data_used": False,
        "independent_verification": False,
    }
    record["evidence_sha256"] = sha256(json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()
    return record
