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


MAX_PLANNER_ATTEMPTS = 3


def _inherit_observations(evidence, prior):
    """Keep completed outputs addressable across distinct recovery generations.

    The current parent's completed map retains the original contract. Older
    observations are indexed by actual plan ID to prevent step-number collisions.
    No new outcome is inferred and no failed output is promoted to a success.
    """
    previous = prior.get("completed_by_plan", {})
    history = dict(previous)
    if prior.get("parent"):
        history[prior["parent"]] = prior.get("completed", {})
    history[evidence["parent"]] = evidence["completed"]
    evidence["completed_by_plan"] = history
    evidence["reference_contract"] = (
        'Use {"$input":["__recovery","completed_by_plan",PLAN_ID,STEP_KEY,FIELD]} '
        'with the actual plan ID and string step key. Reuse completed outputs '
        'from any ancestor rather than executing those tools again.')
    return evidence


class DurableRecovery:
    def __init__(self, orchestrator):
        self.owner = orchestrator
        self.store = orchestrator.store
        self.store._conn().executescript(SCHEMA)
        columns = {row[1] for row in self.store._conn().execute(
            'PRAGMA table_info(bean_orchestration_recovery)')}
        if 'attempts' not in columns:
            self.store._conn().execute(
                'ALTER TABLE bean_orchestration_recovery ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
        # Recover pre-migration failures once instead of treating them as terminal.
        self.store._conn().execute(
            "UPDATE bean_orchestration_recovery SET state='pending',attempts=1 "
            "WHERE state='planner_failed' AND attempts=0")
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
            if existing and (existing["state"] != "pending" or
                             existing["attempts"] >= MAX_PLANNER_ATTEMPTS):
                continue
            ancestor = self.store.fetchone(
                "SELECT depth,evidence_json FROM bean_orchestration_recovery WHERE child_id=?", (parent,))
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
                prior = json.loads(ancestor["evidence_json"]) if ancestor else {}
                _inherit_observations(evidence, prior)
                self.store.execute(
                    "INSERT INTO bean_orchestration_recovery "
                    "(parent_id,child_id,depth,evidence_json,state,error) VALUES (?,?,?,?,?,?)",
                    (parent, child, depth, json.dumps(evidence, allow_nan=False),
                     "pending", None))
                self.store.commit()
            try:
                inputs = dict(detail["inputs"])
                inputs["__recovery"] = evidence
                self.owner.submit(detail["objective"], inputs=inputs, plan_id=child,
                                  recovery_context=evidence)
            except Exception as exc:
                # Persist failed attempts and retry on a later poll, including after restart.
                self.store.execute(
                    "UPDATE bean_orchestration_recovery SET attempts=attempts+1, "
                    "state=CASE WHEN attempts+1>=? THEN 'planner_failed' ELSE 'pending' END, "
                    "error=? WHERE parent_id=?", (MAX_PLANNER_ATTEMPTS, repr(exc)[:1000], parent))
            else:
                self.store.execute(
                    "UPDATE bean_orchestration_recovery SET state='submitted',error=NULL,attempts=attempts+1 "
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
                            "error": row["error"], "attempts": row["attempts"],
                            "plan": self.owner.status(child) if row["state"] == "submitted" else None})
            parent = child
        result["recovery_lineage"] = lineage
        result["effective_status"] = (lineage[-1]["plan"]["status"]
                                      if lineage and lineage[-1]["state"] == "submitted"
                                      else result["status"])
        return result
