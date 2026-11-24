"""Regression of the failed retained workflow experiment; synthetic oracle."""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from bean.runtime.verified_workflows import (
    VerifiedWorkflows, normalize_args, referenced_input_digest,
    register_verified_workflows
)


class Store:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.execute("CREATE TABLE IF NOT EXISTS cognition_goal_proposals "
                        "(proposal_id TEXT PRIMARY KEY, action_detail TEXT)")
    def _conn(self): return self.db
    def commit(self): self.db.commit()
    def execute(self,*args): return self.db.execute(*args)
    def fetchone(self,*args): return self.db.execute(*args).fetchone()


class Owner:
    def __init__(self,path):
        from bean.runtime.portable_skills import group_csv_sum
        self.store=Store(path)
        self.session_uuid="synthetic-owner"
        self.tools={"group_csv_sum":("group",lambda args,ref:group_csv_sum(**args))}
        self.statuses={}
        self.submissions=[]
        self.engine=SimpleNamespace(propose_plan=lambda *args:self.submissions.append(args))
    def status(self,plan_id): return self.statuses[plan_id]
    def _validate_refs(self,args,index):
        from bean.runtime.native_orchestration import NativeOrchestrator
        NativeOrchestrator._validate_refs(self,args,index)
    def record(self,plan,inputs):
        args={k:inputs[k] for k in ("text","group","value")}
        out=self.tools["group_csv_sum"][1](args,plan)
        self.store.execute("INSERT INTO cognition_goal_proposals VALUES (?,?)",
                           (plan,json.dumps({"tool":"group_csv_sum","args":args,"inputs":inputs})))
        self.store.commit()
        self.statuses[plan]={"status":"completed","steps":[{"proposal_id":plan,"output":out}]}


def test_exact_literal_lifting_and_rejection():
    assert normalize_args({"domains":{"a":[1,2]},"constraints":[]},
                          {"domains":{"a":[1,2]},"constraints":[]}) == {
        "domains":{"$input":["domains"]},"constraints":{"$input":["constraints"]}}
    with pytest.raises(ValueError):
        normalize_args({"values":[1,2]},{"other":[1,2]})
    with pytest.raises(ValueError):
        normalize_args({"delta_v_km_s":3.2},{"altitude_km":3.2})
    assert normalize_args({"a":{"$step":0,"path":["value"]}}, {})=={
        "a":{"$step":0,"path":["value"]}}


def test_irrelevant_inputs_do_not_inflate_distinct_training():
    graph=[{"tool":"profile_csv","args":{"text":{"$input":["text"]}}}]
    assert referenced_input_digest(graph,{"text":"a","noise":1})==referenced_input_digest(
        graph,{"text":"a","noise":2})
    assert referenced_input_digest(graph,{"text":"a"})!=referenced_input_digest(
        graph,{"text":"b"})


def test_retain_and_reuse_actual_portable_skill_after_restart(tmp_path):
    path=tmp_path/"workflow.db"
    owner=Owner(path)
    workflows=VerifiedWorkflows(owner)
    for plan,text,total in (("first","g,n\na,0.1\na,0.2","0.3"),
                            ("second","g,n\na,7\na,-2","5")):
        owner.record(plan,{"text":text,"group":"g","value":"n"})
        r=workflows.feedback(family="decimal-groups",plan_id=plan,
            checks=[{"step":0,"path":["groups"],"expected":[{"group":"a","count":2,"sum":total}]}],
            evidence_ref="independent-fixed-oracle:"+plan)
        assert r["passed"]
    owner.store.db.close()
    restarted=Owner(path)
    memory=VerifiedWorkflows(restarted)
    candidates=memory.candidates("decimal-groups")
    assert len(candidates)==1 and candidates[0]["distinct_verified_inputs"]==2
    fresh={"text":"g,n\na,1.25\na,2.75","group":"g","value":"n"}
    report=memory.reuse(family="decimal-groups",inputs=fresh,plan_id="third")
    assert report["model_invoked"] is False
    session,pid,proposals=restarted.submissions[0]
    assert pid=="third" and len(proposals)==1
    detail=proposals[0].action_detail
    from bean.runtime.native_orchestration import NativeOrchestrator
    resolver=object.__new__(NativeOrchestrator)
    resolved=resolver._resolve(detail["args"],{},fresh)
    out=restarted.tools[detail["tool"]][1](resolved,pid)
    assert out["groups"]==[{"group":"a","count":2,"sum":"4"}]


def test_distinct_referenced_inputs_required(tmp_path):
    owner=Owner(tmp_path/"workflow.db")
    memory=VerifiedWorkflows(owner)
    for i in range(2):
        pid="trial-"+str(i)
        owner.record(pid,{"text":"g,n\na,1","group":"g","value":"n","irrelevant":i})
        assert memory.feedback(family="same",plan_id=pid,checks=[
            {"step":0,"path":["groups",0,"sum"],"expected":"1"}],evidence_ref=pid)["passed"]
    assert not memory.candidates("same")
    assert memory.reuse(family="same",inputs={},plan_id="new")["status"]=="abstain"


def test_feedback_remains_host_inbox_only(tmp_path):
    owner=Owner(tmp_path/"workflow.db")
    commands={}
    register_verified_workflows(SimpleNamespace(register=lambda n,f:commands.update({n:f})),owner)
    assert "cognition_workflow_feedback" in commands
    assert "cognition_workflow_feedback" not in owner.tools
