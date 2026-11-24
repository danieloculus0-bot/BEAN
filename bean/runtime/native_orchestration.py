"""Compose existing BEAN capabilities in model-selected, durable GoalCycle plans.

Revision 2026-11-23: native orchestration uses the running Core's model,
registered tools, canonical SQLite and GoalCycle; no second brain or daemon.
Execution receipts are not independent correctness verdicts.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine, goal_plan,
    plan_proposal_id,
)
from bean.memory.store import get_store
from bean.learning.reasoning_service import _model_response
from bean.modules import builtin
from bean.optimization.skill_incubator import evaluate_retained_skill

CAPABILITY = "native_orchestration_step"

OUTPUT_SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_orchestration_outputs (
    proposal_id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    output_json TEXT NOT NULL,
    output_sha256 TEXT NOT NULL
);
"""


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _digest(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _path(value, parts):
    if not isinstance(parts, list):
        raise ValueError("reference path must be a list")
    for part in parts:
        value = value[part]
    return value


class NativeOrchestrator:
    """Plan with the configured model, execute with GoalCycle, reuse outputs."""

    def __init__(self, core, cycle, *, session_uuid, skill_catalog=None,
                 skill_action=None, skill_db=None, transfer_projects=None):
        self.core = core
        self.cycle = cycle
        self.session_uuid = session_uuid
        self.store = get_store()
        self.store._conn().executescript(OUTPUT_SCHEMA)
        self.store.commit()
        self.engine = GoalStateEngine()
        self.tools = {}
        self.register("numeric_context", "Analyze history: {history:[numbers],window:int}",
                      self._builtin(builtin.numeric_context))
        self.register("last_sign", "Predict sign: {history:[numbers]}",
                      self._builtin(builtin.predict_last_sign))
        self.register("mean_sign", "Predict mean sign: {history:[numbers]}",
                      self._builtin(builtin.predict_mean_sign))
        self.register("memory_recall", "Recall current or specified session: {limit:int}",
                      self._builtin(builtin.memory_recall))
        self.register("drive_status", "Read current drives: {}",
                      self._builtin(builtin.evaluate_drives))
        self.register("reason", "Core reasoning: {domain:str,query:str}",
                      self._reason)
        self.register("reason_local", "Native symbolic reasoning: {domain:str,query:str}",
                      self._reason_local)
        if skill_catalog and skill_action and skill_db:
            skills = skill_catalog["skills"]
            self.skill_action = skill_action
            self.skill_db = Path(skill_db)
            self.skills = skills
            self.transfer = {}
            for key, path in (transfer_projects or {}).items():
                skill = skills[key]
                project = Path(path).resolve(strict=True)
                if project in (skill["training_project"], skill["holdout_project"]):
                    raise ValueError("transfer project must differ from acquisition projects")
                if not (project / "tests").is_dir():
                    raise ValueError("transfer project requires host-authored tests")
                self.transfer[key] = project
            self.register("learn_skill",
                          "Acquire/reuse retained source: {skill_id:str}; choices: " +
                          _json({key: item["objective"] for key, item in skills.items()}),
                          self._learn)
            if self.transfer:
                self.register("evaluate_skill",
                              "Execute retained skill on host transfer project: "
                              "{skill_id:str,objective_sha256:str}; choices: " +
                              _json(sorted(self.transfer)), self._reuse)
        self.fallback = cycle.actions.get("run_experiment")
        cycle.actions["run_experiment"] = self.execute

    def register(self, name, description, handler):
        """Host integration point for additional native digital capabilities."""
        if name in self.tools or not callable(handler):
            raise ValueError("duplicate or noncallable orchestration tool")
        self.tools[name] = (description, handler)

    def _builtin(self, fn):
        return lambda args, task_ref: fn(args, {"session_uuid": self.session_uuid})

    def _reason(self, args, task_ref):
        return self.core.reason(domain=args["domain"], task_ref=task_ref,
                                query=args["query"])

    def _reason_local(self, args, task_ref):
        return self.core.reason_local(domain=args["domain"], task_ref=task_ref,
                                      query=args["query"])

    def _learn(self, args, task_ref):
        result = self.skill_action({"action_detail": {
            "capability": "native_skill_incubator", "skill_id": args["skill_id"]}})
        return result

    def _reuse(self, args, task_ref):
        key = args["skill_id"]
        return evaluate_retained_skill(
            self.skill_db, name=self.skills[key]["name"],
            objective=args["objective_sha256"], evaluation_project=self.transfer[key])

    def _validate_refs(self, value, step):
        if isinstance(value, dict):
            if "$step" in value:
                if set(value) - {"$step", "path"} or type(value["$step"]) is not int:
                    raise ValueError("invalid step reference")
                if not 0 <= value["$step"] < step:
                    raise ValueError("references must point to earlier steps")
                if not isinstance(value.get("path", []), list):
                    raise ValueError("reference path must be a list")
            elif "$input" in value:
                if set(value) != {"$input"} or not isinstance(value["$input"], list):
                    raise ValueError("invalid input reference")
            else:
                for item in value.values():
                    self._validate_refs(item, step)
        elif isinstance(value, list):
            for item in value:
                self._validate_refs(item, step)

    def submit(self, objective, *, inputs=None, plan_id=None):
        """The real Core model selects the tools and their data dependencies."""
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("objective is required")
        inputs = {} if inputs is None else inputs
        if not isinstance(inputs, dict):
            raise ValueError("inputs must be an object")
        plan_id = plan_id or "workflow:" + uuid.uuid4().hex
        first_id = plan_proposal_id(plan_id, 0)
        old = self.store.fetchone(
            "SELECT action_detail FROM cognition_goal_proposals WHERE proposal_id=?",
            (first_id,))
        if old:
            detail = json.loads(old["action_detail"])
            if (detail.get("capability") != CAPABILITY or
                    detail.get("objective") != objective or detail.get("inputs") != inputs):
                raise ValueError("plan ID already belongs to a different task")
            return self.status(plan_id)
        prompt = (
            "You are BEAN's task planner. Select a sequence of one to eight tools "
            "to accomplish the objective. Reply ONLY with a JSON object containing "
            "steps, an array of objects each with tool and args. args is an object. "
            "Use a prior result with {\"$step\":0,\"path\":[\"field\"]}; "
            "use input data with {\"$input\":[\"field\"]}. "
            "References may point only to earlier steps. A whole prior result uses "
            "an empty path. Do not invent tool names or observations. "
            "Use the final reason tool if synthesis is needed.\n"
            "Tools: " + _json({k: v[0] for k, v in self.tools.items()}) +
            "\nObjective: " + objective + "\nInputs: " + _json(inputs)
        )
        raw, model, provider, _ = _model_response(
            self.core.model, prompt, "BEAN native capability orchestration")
        if raw.startswith(chr(96) * 3):
            raw = "\n".join(raw.splitlines()[1:-1]).strip()
        plan = json.loads(raw)
        steps = plan["steps"]
        if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
            raise ValueError("model must return one to eight steps")
        proposals = []
        for index, step in enumerate(steps):
            if (not isinstance(step, dict) or set(step) != {"tool", "args"} or
                    step["tool"] not in self.tools or not isinstance(step["args"], dict)):
                raise ValueError("invalid model-selected tool step")
            self._validate_refs(step["args"], index)
            proposals.append(GoalProposal(
                "orchestrate_objective", ActionType.RUN_EXPERIMENT,
                "Execute model-selected capability", 3, ApprovalRequired.NONE,
                {"capability": CAPABILITY, "tool": step["tool"], "args": step["args"],
                 "objective": objective, "inputs": inputs,
                 "planner_model": model, "planner_provider": provider,
                 "learning_context": "orchestration:" + step["tool"]},
                "orchestration"))
        self.engine.propose_plan(self.session_uuid, plan_id, proposals)
        return self.status(plan_id)

    def _read_output(self, proposal_id):
        row = self.store.fetchone(
            "SELECT output_json,output_sha256 FROM bean_orchestration_outputs "
            "WHERE proposal_id=?", (proposal_id,))
        if row is None:
            raise LookupError("previous step has no retained output")
        if _digest(row["output_json"]) != row["output_sha256"]:
            raise ValueError("stored output digest mismatch")
        return json.loads(row["output_json"])

    def _resolve(self, value, plan, inputs):
        if isinstance(value, dict):
            if "$step" in value:
                pid = plan_proposal_id(plan["id"], value["$step"])
                return _path(self._read_output(pid), value.get("path", []))
            if "$input" in value:
                return _path(inputs, value["$input"])
            return {k: self._resolve(v, plan, inputs) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve(v, plan, inputs) for v in value]
        return value

    def execute(self, goal):
        detail = goal.get("action_detail")
        if not isinstance(detail, dict) or detail.get("capability") != CAPABILITY:
            return self.fallback(goal) if self.fallback else {
                "status": "unknown", "reason": "unsupported_experiment"}
        pid = goal["proposal_id"]
        plan = goal_plan(detail, pid)
        if plan is None:
            raise ValueError("orchestration requires persisted plan metadata")
        name = detail["tool"]
        self._validate_refs(detail["args"], plan["step"])
        args = self._resolve(detail["args"], plan, detail["inputs"])
        output = self.tools[name][1](args, pid)
        raw = _json(output)
        digest = _digest(raw)
        self.store.execute(
            "INSERT INTO bean_orchestration_outputs VALUES (?,?,?,?)",
            (pid, name, raw, digest))
        self.store.commit()
        # A completed inference or calculation is an execution outcome, not
        # an independent correctness finding. Failed acquisition/reuse must
        # not release a dependent step as if the requested artifact existed.
        completed = output is not None
        if name == "learn_skill":
            completed = bool(output.get("retained_skill"))
        elif name == "evaluate_skill":
            completed = output.get("passed") is True
        elif isinstance(output, dict):
            completed = str(output.get("status", "")).lower() not in (
                "failed", "failure", "error", "invalid", "unknown")
        return {"status": "success" if completed else "failed", "tool": name,
                "output_sha256": digest, "output_bytes": len(raw.encode("utf-8")),
                "independent_outcome_verified": False}

    def status(self, plan_id):
        result = self.cycle.plan_status(plan_id)
        for step in result["steps"]:
            pid = step["proposal_id"]
            row = self.store.fetchone(
                "SELECT action_detail FROM cognition_goal_proposals WHERE proposal_id=?",
                (pid,))
            if row:
                step["tool"] = json.loads(row["action_detail"]).get("tool")
            try:
                step["output"] = self._read_output(pid)
            except LookupError:
                pass
        return result


def register_orchestration_handlers(inbox, orchestrator):
    inbox.register("cognition_plan", lambda msg, session: orchestrator.submit(
        msg.args["objective"], inputs=msg.args.get("inputs"),
        plan_id=msg.args.get("plan_id")))
    inbox.register("cognition_plan_status", lambda msg, session:
                   orchestrator.status(msg.args["plan_id"]))
