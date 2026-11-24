"""Retain independently checked, input-parameterized native GoalCycle procedures.

The trusted local inbox supplies outcome checks. A model cannot approve itself.
Only read-only tools are eligible; no code generation or external effects.
"""
import hashlib
import json
import math

from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, plan_proposal_id
from bean.runtime.native_orchestration import CAPABILITY

SAFE_TOOLS = frozenset(("numeric_context","last_sign","mean_sign","orbit_reference",
    "vis_viva_reference","acceleration_reference","compare_numeric",
    "earth_projectile_reference","hohmann_reference","solve_constraints",
    "retained_weighted_mean","reason_local","reason_composed","plan_state"))
SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_verified_workflow_trials (
  family TEXT NOT NULL, plan_id TEXT PRIMARY KEY, graph_sha TEXT NOT NULL,
  graph_json TEXT NOT NULL, input_sha TEXT NOT NULL, evidence_json TEXT NOT NULL,
  passed INTEGER NOT NULL
);
"""


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def at_path(value,path):
    if not isinstance(path,list) or len(path)>16:
        raise ValueError("invalid path")
    for key in path:
        if type(key) not in (str,int):
            raise ValueError("invalid path key")
        value=value[key]
    return value


def input_refs(value):
    """Accept references and containers only; no training input literals."""
    if isinstance(value,dict):
        if "$input" in value:
            if set(value)!={"$input"} or not isinstance(value["$input"],list):
                raise ValueError("invalid input reference")
            return 1
        if "$step" in value:
            if set(value)-{"$step","path"}:raise ValueError("invalid step reference")
            return 0
        if not value:raise ValueError("empty argument map")
        return sum(input_refs(v) for v in value.values())
    if isinstance(value,list) and value:
        return sum(input_refs(v) for v in value)
    raise ValueError("workflow must use input or prior-result references, not literal data")


def abstract_args(value,inputs,outputs,*,hint=None):
    """Recover exact observed bindings, refusing ambiguous literals.

    Prefer a same-named input field when equal, otherwise require a unique
    matching input or prior output. No invented constants or fuzzy matching.
    """
    if isinstance(value,dict) and ("$input" in value or "$step" in value):
        return value
    if hint in inputs and canonical(inputs[hint])==canonical(value):
        return {"$input":[hint]}
    candidates=[]
    def walk(obj,path,ref):
        if canonical(obj)==canonical(value):
            candidates.append(ref(path))
        if isinstance(obj,dict):
            for k,v in obj.items():walk(v,path+[k],ref)
    walk(inputs,[],lambda p:{"$input":p})
    for i,out in enumerate(outputs):
        if out is not None:walk(out,[],lambda p,i=i:{"$step":i,"path":p})
    if len(candidates)==1:return candidates[0]
    if isinstance(value,dict) and value:
        return {k:abstract_args(v,inputs,outputs,hint=k) for k,v in value.items()}
    if isinstance(value,list) and value:
        return [abstract_args(v,inputs,outputs) for v in value]
    raise ValueError("unbound or ambiguous training literal")


def match(actual,expected):
    if type(expected) in (int,float):
        return type(actual) in (int,float) and math.isfinite(actual) and math.isfinite(expected) and math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-9)
    return type(actual) is type(expected) and actual==expected


class VerifiedWorkflows:
    def __init__(self,owner):
        self.owner=owner
        self.store=owner.store
        self.store._conn().executescript(SCHEMA)
        self.store.commit()

    def feedback(self,*,family,plan_id,checks,evidence_ref):
        if not isinstance(family,str) or not 1<=len(family)<=100:
            raise ValueError("bounded family required")
        if not isinstance(evidence_ref,str) or not 1<=len(evidence_ref)<=500:
            raise ValueError("independent evaluator reference required")
        if not isinstance(checks,list) or not 1<=len(checks)<=32:
            raise ValueError("checks required")
        status=self.owner.status(plan_id)
        if status["status"] not in ("completed","failed"):
            raise ValueError("terminal plan required")
        graph=[];observed=[];inputs=None
        for i,step in enumerate(status["steps"]):
            row=self.store.fetchone("SELECT action_detail FROM cognition_goal_proposals WHERE proposal_id=?",(step["proposal_id"],))
            detail=json.loads(row["action_detail"])
            if detail["tool"] not in SAFE_TOOLS or detail["tool"] not in self.owner.tools:
                raise ValueError("ineligible tool")
            self.owner._validate_refs(detail["args"],i)
            if inputs is None:inputs=detail["inputs"]
            elif inputs!=detail["inputs"]:raise ValueError("inconsistent plan inputs")
            args={k:abstract_args(v,inputs,observed,hint=k) for k,v in detail["args"].items()}
            self.owner._validate_refs(args,i)
            input_refs(args)
            graph.append({"tool":detail["tool"],"args":args})
            observed.append(step.get("output"))
        if not graph or not any(input_refs(x["args"]) for x in graph):
            raise ValueError("must depend on new inputs")
        covered=set();outcomes=[]
        for check in checks:
            if not isinstance(check,dict) or set(check)!={"step","path","expected"}:
                raise ValueError("invalid outcome check")
            idx=check["step"]
            if type(idx) is not int or not 0<=idx<len(graph):raise ValueError("step index")
            covered.add(idx)
            try: actual=at_path(observed[idx],check["path"]);ok=match(actual,check["expected"])
            except (KeyError,IndexError,TypeError):actual=None;ok=False
            outcomes.append({**check,"actual":actual,"matched":ok})
        if covered!=set(range(len(graph))):raise ValueError("each step needs an independent outcome check")
        passed=status["status"]=="completed" and all(x["matched"] for x in outcomes)
        row=(family,plan_id,digest(graph),canonical(graph),digest(inputs),
             canonical({"source":evidence_ref,"checks":outcomes}),int(passed))
        old=self.store._conn().execute("SELECT family,plan_id,graph_sha,graph_json,input_sha,evidence_json,passed FROM bean_verified_workflow_trials WHERE plan_id=?",(plan_id,)).fetchone()
        if old is not None and tuple(old)!=row:raise ValueError("feedback immutable")
        self.store.execute("INSERT OR IGNORE INTO bean_verified_workflow_trials VALUES (?,?,?,?,?,?,?)",row)
        self.store.commit()
        return {"passed":passed,"graph_sha":row[2],"input_sha":row[4],"checks":outcomes}

    def candidates(self,family):
        rows=self.store._conn().execute(
            "SELECT graph_sha,graph_json,COUNT(DISTINCT CASE WHEN passed=1 THEN input_sha END),SUM(CASE WHEN passed=0 THEN 1 ELSE 0 END) FROM bean_verified_workflow_trials WHERE family=? GROUP BY graph_sha,graph_json ORDER BY 3 DESC,graph_sha",(family,)).fetchall()
        return [{"graph_sha":r[0],"graph":json.loads(r[1]),"distinct_verified_inputs":r[2],"failures":r[3]} for r in rows if r[2]>=2 and r[3]==0 and digest(json.loads(r[1]))==r[0]]

    def reuse(self,*,family,inputs,plan_id,graph_sha=None):
        if not isinstance(inputs,dict):raise ValueError("inputs object required")
        chosen=[r for r in self.candidates(family) if graph_sha is None or r["graph_sha"]==graph_sha]
        if len(chosen)!=1:return {"status":"abstain","reason":"no uniquely verified workflow"}
        row=chosen[0];graph=row["graph"];proposals=[]
        # Validate tool contracts and input paths before queueing immutable goals.
        def validate(value):
            if isinstance(value,dict):
                if "$input" in value:at_path(inputs,value["$input"])
                elif "$step" not in value:
                    for x in value.values():validate(x)
            elif isinstance(value,list):
                for x in value:validate(x)
        for i,step in enumerate(graph):
            if step["tool"] not in SAFE_TOOLS or step["tool"] not in self.owner.tools:
                raise ValueError("tool unavailable")
            self.owner._validate_refs(step["args"],i);validate(step["args"])
            proposals.append(GoalProposal("orchestrate_objective",ActionType.RUN_EXPERIMENT,
                "Execute independently checked retained procedure",3,ApprovalRequired.NONE,
                {"capability":CAPABILITY,"tool":step["tool"],"args":step["args"],
                 "objective":"Verified workflow reuse: "+family,"inputs":inputs,
                 "planner_model":None,"planner_provider":"verified_workflow",
                 "workflow_sha":row["graph_sha"],"learning_context":"workflow:"+family},
                "orchestration"))
        self.owner.engine.propose_plan(self.owner.session_uuid,plan_id,proposals)
        return {"status":"submitted","plan_id":plan_id,"graph_sha":row["graph_sha"],"model_invoked":False}


def register_verified_workflows(inbox,owner):
    memory=VerifiedWorkflows(owner)
    inbox.register("cognition_workflow_feedback",lambda msg,session:memory.feedback(**msg.args))
    inbox.register("cognition_workflow_reuse",lambda msg,session:memory.reuse(**msg.args))
    inbox.register("cognition_workflow_inventory",lambda msg,session:{"candidates":memory.candidates(msg.args["family"])})
    owner.verified_workflows=memory
