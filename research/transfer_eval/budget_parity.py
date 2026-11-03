"""Audit externally reported paired budgets; not independently verified execution."""
BUDGET_KEYS = ("inference_tokens", "tool_calls", "training_updates")

def audit_budget_parity(rows):
    """Reject candidate resource advantage on any paired case, not just totals."""
    trials = list(rows)
    if not trials:
        raise ValueError("no trials")
    seen = set()
    violations = []
    totals = {side: {key: 0 for key in BUDGET_KEYS} for side in ("baseline", "candidate")}
    for trial in trials:
        if not isinstance(trial, dict):
            raise ValueError("trial must be a mapping")
        case = trial.get("case_id")
        if not isinstance(case, str) or not case.strip() or case != case.strip() or case in seen:
            raise ValueError("missing or duplicate case_id")
        seen.add(case)
        for side in ("baseline", "candidate"):
            budget = trial.get(side)
            if not isinstance(budget, dict) or set(budget) != set(BUDGET_KEYS):
                raise ValueError("incomplete " + side + " budget")
            for key in BUDGET_KEYS:
                value = budget[key]
                if type(value) is not int or value < 0:
                    raise ValueError("budget must be nonnegative integer")
                totals[side][key] += value
        for key in BUDGET_KEYS:
            if trial["candidate"][key] > trial["baseline"][key]:
                violations.append({"case_id": case, "resource": key,
                                   "baseline": trial["baseline"][key],
                                   "candidate": trial["candidate"][key]})
    return {"paired_cases": len(trials), "candidate_not_advantaged": not violations,
            "violations": violations, "totals": totals,
            "claim": "reported_budget_audit_only_not_verified_execution"}
