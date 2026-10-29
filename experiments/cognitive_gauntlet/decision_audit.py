"""Post-hoc decision-quality audit for frozen cognitive-gauntlet case receipts.

This module never selects or trains a policy. It distinguishes predictive
calibration, actual mistakes, and decision stability from switching speed.
Scoring uses outcomes only AFTER forecasts have already been recorded.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math

SCHEMA = "bean.gauntlet.decision_quality.v1"
SWITCH_COSTS = (0.0, 0.02, 0.10)


def _summarize(rows, arms, *, bins=10):
    n = len(rows)
    if not n:
        raise ValueError("cannot summarize empty cases")
    output = {"cases": n, "arms": {}}
    for arm in arms:
        brier = logloss = wrong = high_conf_wrong = switches = 0
        previous = {}
        counts = [0] * bins
        confidences = [0.0] * bins
        outcomes = [0.0] * bins
        for row in rows:
            p = row["predictions"][arm]
            truth = row["truth_revealed_after_forecast"]
            brier += (p - truth) ** 2
            logloss -= truth * math.log(max(p, 1e-12)) + (1 - truth) * math.log(max(1 - p, 1e-12))
            action = int(p >= 0.5)
            wrong += int(action != truth)
            high_conf_wrong += int(action != truth and max(p, 1 - p) >= 0.9)
            bucket = min(bins - 1, int(p * bins))
            counts[bucket] += 1
            confidences[bucket] += p
            outcomes[bucket] += truth
            key = (row["regime"], row["seed"])
            if key in previous:
                switches += int(previous[key] != action)
            previous[key] = action
        ece = sum(abs(confidences[i] - outcomes[i]) for i in range(bins)) / n
        output["arms"][arm] = {
            "brier": brier / n,
            "log_loss": logloss / n,
            "classification_error": wrong / n,
            "high_confidence_mistakes": high_conf_wrong,
            "calibration_error_10bin": ece,
            "decision_switches": switches,
            "decision_cost_sensitivity": {
                str(cost): (wrong + cost * switches) / n for cost in SWITCH_COSTS
            },
        }
    if all("mode" in row for row in rows):
        mode_changes = 0
        previous_mode = {}
        for row in rows:
            key = (row["regime"], row["seed"])
            mode = row["mode"]
            if key in previous_mode:
                mode_changes += int(previous_mode[key] != mode)
            previous_mode[key] = mode
        output["dual_state"] = {
            "chaos_predictions": sum(row["mode"] == "parallel_chaos" for row in rows),
            "mode_changes": mode_changes,
        }
    return output


def audit_cases(cases, arms, *, source_digest=None):
    """Audit case-level predictions without selecting winners or tuning thresholds.

    Requires every sequential case per (regime, seed) from step 0. The
    original cases remain authoritative, and no failed case is filtered out.
    """
    if not isinstance(cases, list) or not cases:
        raise ValueError("nonempty case list required")
    if (not isinstance(arms, (tuple, list)) or not arms or
            any(not isinstance(a, str) or not a for a in arms) or
            len(set(arms)) != len(arms)):
        raise ValueError("invalid arm names")
    if source_digest is not None and (not isinstance(source_digest, str) or
                                     len(source_digest) != 64 or
                                     any(c not in "0123456789abcdef" for c in source_digest)):
        raise ValueError("invalid source digest")
    last_steps = {}
    grouped = defaultdict(list)
    ordered = []
    for row in cases:
        if not isinstance(row, dict):
            raise ValueError("invalid case receipt")
        regime, seed, step = row["regime"], row["seed"], row["step"]
        truth = row["truth_revealed_after_forecast"]
        if (not isinstance(regime, str) or not regime or
                type(seed) is not int or type(step) is not int or step < 0 or
                type(truth) is not int or truth not in (0, 1)):
            raise ValueError("invalid case identity or outcome")
        key = (regime, seed)
        if step != last_steps.get(key, -1) + 1:
            raise ValueError("missing, duplicate or reordered case step")
        last_steps[key] = step
        predictions = row.get("predictions")
        if not isinstance(predictions, dict) or set(predictions) != set(arms):
            raise ValueError("prediction arm coverage mismatch")
        for arm in arms:
            p = predictions[arm]
            if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError("invalid prediction")
            if "losses" in row:
                reported = row["losses"].get(arm)
                if (type(reported) not in (int, float) or not math.isfinite(reported)
                        or not math.isclose(reported, (p-truth)**2, rel_tol=1e-10, abs_tol=1e-12)):
                    raise ValueError("case loss mismatch")
        if "mode" in row and row["mode"] not in ("remember", "parallel_chaos"):
            raise ValueError("invalid dual-state mode")
        grouped[regime].append(row)
        ordered.append(row)
    by_regime = {regime: _summarize(grouped[regime], arms)
                 for regime in sorted(grouped)}
    report = {
        "schema": SCHEMA,
        "source_digest": source_digest,
        "evaluation": "post-hoc scoring of frozen synthetic predictions; no policy tuning",
        "metric_notes": {
            "brier": "proper probability score, lower is better",
            "log_loss": "proper probability score, lower is better; probabilities clipped at 1e-12 for finite reporting",
            "classification_error": "binary decisions at probability 0.5; lower is better",
            "calibration_error_10bin": "10-bin expected calibration error, descriptive and sample-dependent",
            "high_confidence_mistakes": "incorrect binary decisions at confidence >= 0.9",
            "decision_cost_sensitivity": "0-1 errors plus hypothetical per-decision-switch cost; not a learned utility function",
            "decision_switches": "changes in thresholded action, not elapsed reasoning time",
        },
        "overall": _summarize(ordered, arms),
        "by_regime": by_regime,
    }
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["audit_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    return report
