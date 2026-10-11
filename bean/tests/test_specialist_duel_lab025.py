"""Offline tests. Mock agents cannot supply evidence of model intelligence."""
from __future__ import annotations
import json
import subprocess
import pytest
from experiments.agent_arena import specialist_duel_lab025 as duel
from experiments.agent_arena.specialist_cases_lab025 import CASES,public_case,digest


class FictionalProvider:
    model="qwen2.5-coder:1.5b"
    def preflight(self): return {"ready":True}


def fake_bean(client,public,original,previous,feedback,history,iteration):
    assert len(history)==iteration-1
    assert original==public["source"]
    return original+"\n# synthetic_bean_round"+str(iteration)+"\n","candidate",None


def fake_opponent(name,client,public,previous,feedback,iteration):
    assert name in CASES
    return public["source"]+"\n# synthetic_agent_round"+str(iteration)+"\n","candidate",None


def dev_grader(src,suite):
    assert "unittest" in suite
    score=3 if "bean_round3" in src else 2 if "bean_round2" in src else 1
    return {"status":"failed","passed":score,"total":3}


def holdout_grader(src,suite):
    assert "unittest" in suite
    result=7 if "bean_round3" in src else 2
    return {"status":"failed","passed":result,"total":8}


@pytest.mark.parametrize("name",list(CASES))
def test_all_five_mock_contracts_and_real_journal(tmp_path,name):
    root=tmp_path/name
    x=duel.author(name,root,client=FictionalProvider(),
          bean_writer=fake_bean,opponent_writer=fake_opponent,grader=dev_grader)
    assert x["rounds"]==3
    assert x["agents"]["bean"]["selected_round"]==3
    y=duel.judge(name,root,grader=holdout_grader)
    assert y["classification"]=="BEAN_WIN"
    assert y["journal_verified"]
    assert y["results"]["bean"]["passed"]==7
    assert json.loads((root/"verdict.json").read_text())["evidence_sha256"]==y["evidence_sha256"]


def test_missing_opponent_does_not_count_as_win(tmp_path):
    def missing(*args):
        return None,"tool_failure",{"reason":"missing_agent_install"}
    root=tmp_path/"missing"
    duel.author("goose",root,client=FictionalProvider(),
                bean_writer=fake_bean,opponent_writer=missing,grader=dev_grader)
    r=duel.judge("goose",root,grader=holdout_grader)
    assert r["classification"]=="INCONCLUSIVE"


def test_reject_changed_source(tmp_path):
    root=tmp_path/"tampered"
    duel.author("cline",root,client=FictionalProvider(),
                bean_writer=fake_bean,opponent_writer=fake_opponent,grader=dev_grader)
    (root/"candidates"/"bean"/"round1.py").write_text("def trap(): pass")
    with pytest.raises(ValueError,match="digest"):
        duel.judge("cline",root,grader=holdout_grader)


def test_developer_judge_has_no_network_or_token():
    calls=[]
    def runner(cmd,**kwargs):
        calls.append((cmd,kwargs))
        return subprocess.CompletedProcess(cmd,1,stdout="",stderr="Ran 3 tests in 0.02s\nFAILED (failures=2)")
    data=duel.isolated_test("def f():return 1",CASES["continue"]["dev"],runner=runner)
    assert data["passed"]==1 and data["total"]==3
    cmd,kwargs=calls[0]
    assert cmd[cmd.index("--network")+1]=="none"
    assert "--read-only" in cmd and "--cap-drop" in cmd
    assert kwargs["env"].keys()=={"PATH"}


def test_real_model_unavailable_fails_closed(tmp_path):
    class Absent(FictionalProvider):
        def preflight(self): raise RuntimeError("not downloaded")
    with pytest.raises(RuntimeError,match="not downloaded"):
        duel.author("opencode",tmp_path/"out",client=Absent(),
            bean_writer=fake_bean,opponent_writer=fake_opponent,grader=dev_grader)


def test_no_prior_reuse(tmp_path):
    root=tmp_path/"run"
    root.mkdir()
    (root/"history.txt").write_text("prior run")
    with pytest.raises(ValueError,match="empty"):
        duel.author("opencode",root,client=FictionalProvider(),
            bean_writer=fake_bean,opponent_writer=fake_opponent,grader=dev_grader)


def test_public_manifest_is_predeclared():
    d=digest()
    assert len(CASES)==5
    assert len({x["holdout"] for x in d.values()})==5
    for name,task in CASES.items():
        assert public_case(name)["source_sha256"]
        assert "unittest" in task["dev"] and "unittest" in task["holdout"]
        assert task["dev"]!=task["holdout"]
