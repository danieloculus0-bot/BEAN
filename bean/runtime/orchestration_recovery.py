"""Recovery of failed native plans without replaying completed steps."""
import hashlib
import json

SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_orchestration_recovery (
 parent_id TEXT PRIMARY KEY, child_id TEXT NOT NULL UNIQUE,
 depth INTEGER NOT NULL, evidence_json TEXT NOT NULL,
 state TEXT NOT NULL, error TEXT
);
"""


class DurableRecovery:
    def __init__(self, orchestrator):
        self.owner = orchestrator
        self.store = orchestrator.store
        self.store._conn().executescript(SCHEMA)
        self.store.commit()
        self.original_poll = orchestrator.cycle.poll_due
        orchestrator.cycle.poll_due = self.poll

    def poll(self, *, max_goals=1):
        outcomes = self.original_poll(max_goals=max_goals)
        self.advance()
        return outcomes

    def advance(self):
        # Scan persisted failures, including those from a previous process.
        rows = self.store.fetchall(
            "SELECT proposal_id,action_detail FROM cognition_goal_proposals "
            "WHERE status='failed'")
        from bean.cognition.goal_state import goal_plan
        from bean.runtime.native_orchestration import CAPABILITY
        for row in rows:
            detail = json.loads(row["action_detail"])
            if detail.get("capability") != CAPABILITY:
                continue
            plan = goal_plan(detail, row["proposal_id"])
            if plan is None:
                continue
            parent = plan["id"]
            existing = self.store.fetchone(
                "SELECT * FROM bean_orchestration_recovery WHERE parent_id=?", (parent,))
            if existing and existing["state"] != "pending":
                continue
            ancestor = self.store.fetchone(
                "SELECT depth FROM bean_orchestration_recovery WHERE child_id=?", (parent,))
            depth = (ancestor["depth"] if ancestor else 0) + 1
            if depth > 3:
                continue
            status = self.owner.status(parent)
            if status["status"] != "failed":
                continue
            if any(s["status"] in ("running", "needs_review") for s in status["steps"]):
                continue
            if existing:
                child = existing["child_id"]
                evidence = json.loads(existing["evidence_json"])
            else:
                child = "recovery:" + hashlib.sha256(parent.encode()).hexdigest()
                evidence = {"parent": parent, "completed": {}, "failures": []}
                for step in status["steps"]:
                    if step["status"] == "completed" and "output" in step:
                        evidence["completed"][str(step["step"])] = step["output"]
                    elif step["status"] == "failed":
                        run = self.store.fetchone(
                            "SELECT error,result_json FROM bean_goal_runs WHERE proposal_id=? "
                            "ORDER BY started_at DESC LIMIT 1", (step["proposal_id"],))
                        evidence["failures"].append({
                            "tool": step.get("tool"), "output": step.get("output"),
                            "receipt": dict(run) if run else None})
                self.store.execute(
                    "INSERT INTO bean_orchestration_recovery VALUES (?,?,?,?,?,?)",
                    (parent, child, depth, json.dumps(evidence, allow_nan=False),
                     "pending", None))
                self.store.commit()
            try:
                inputs = dict(detail["inputs"])
                inputs["__recovery"] = evidence
                self.owner.submit(detail["objective"], inputs=inputs, plan_id=child,
                                  recovery_context=evidence)
            except Exception as exc:
                self.store.execute(
                    "UPDATE bean_orchestration_recovery SET state='planner_failed',error=? "
                    "WHERE parent_id=?", (repr(exc)[:1000], parent))
            else:
                self.store.execute(
                    "UPDATE bean_orchestration_recovery SET state='submitted',error=NULL "
                    "WHERE parent_id=?", (parent,))
            self.store.commit()
            # One model recovery request per polling cycle.
            break

    def status(self, plan_id):
        result = self.owner.status(plan_id)
        lineage = []
        parent = plan_id
        while True:
            row = self.store.fetchone(
                "SELECT * FROM bean_orchestration_recovery WHERE parent_id=?", (parent,))
            if row is None:
                break
            child = row["child_id"]
            lineage.append({"parent": parent, "child": child, "state": row["state"],
                            "error": row["error"], "plan": self.owner.status(child)})
            parent = child
        result["recovery_lineage"] = lineage
        result["effective_status"] = (lineage[-1]["plan"]["status"]
                                      if lineage and lineage[-1]["state"] == "submitted"
                                      else result["status"])
        return result
