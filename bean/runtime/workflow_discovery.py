"""Recall independently verified workflows using the original task objective."""


def discover_verified_workflow(conn, objective, candidates):
    """Return a unique eligible family/graph pair, or None.

    The existing trial ledger establishes eligibility; persisted native goal
    records establish the objective. Exact matching deliberately avoids
    asserting semantic transfer from textual similarity.
    """
    rows = conn.execute("""
        SELECT DISTINCT t.family, t.graph_sha
        FROM bean_verified_workflow_trials AS t
        JOIN cognition_goal_proposals AS p
          ON json_extract(p.action_detail, '$.goal_plan.id') = t.plan_id
         AND json_extract(p.action_detail, '$.goal_plan.step') = 0
        WHERE t.passed = 1 AND p.status = 'completed'
          AND json_extract(p.action_detail, '$.capability') = 'native_orchestration_step'
          AND json_extract(p.action_detail, '$.objective') = ?
          AND COALESCE(json_extract(p.action_detail, '$.planner_provider'), '')
              NOT IN ('candidate_validation', 'verified_workflow')
    """, (objective,)).fetchall()
    eligible = {}
    found = []
    for family, graph_sha in rows:
        if family not in eligible:
            eligible[family] = {row['graph_sha'] for row in candidates(family)}
        if graph_sha in eligible[family]:
            found.append((family, graph_sha))
    return found[0] if len(found) == 1 else None
