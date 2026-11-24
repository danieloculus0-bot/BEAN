import pytest
from decimal import Decimal
from random import Random
from bean.runtime.portable_skills import (
    profile_csv, group_csv_sum, search_transcript, register_portable_skills
)


def test_csv_profile_quoted_and_missing():
    r=profile_csv('name,value\n"a,b",1\n"a,b",\nc,2\n')
    assert r=={"row_count":3,"columns":{"name":{"present":3,"missing":0,"distinct":2},
                                      "value":{"present":2,"missing":1,"distinct":2}}}


@pytest.mark.parametrize("text",["a,a\n1,2","a,b\n1","a\n1,2","\n","a,\n1,2"])
def test_invalid_csv(text):
    with pytest.raises(ValueError):
        profile_csv(text)


def test_exact_decimal_aggregation():
    r=group_csv_sum("g,n\na,0.1\na,0.2\nb,-2.5\na,-0.03\n","g","n")
    assert r["groups"]==[{"group":"a","count":3,"sum":"0.27"},{"group":"b","count":1,"sum":"-2.5"}]


@pytest.mark.parametrize("value",["NaN","Infinity","1e99","bad"])
def test_bad_decimal(value):
    with pytest.raises(ValueError):
        group_csv_sum("g,n\na,"+value,"g","n")


def test_independent_randomized_integer_cents():
    rng=Random(1779)
    for _ in range(40):
        totals={}
        counts={}
        lines=["g,n"]
        for _ in range(50):
            g=rng.choice("abcd")
            n=rng.randrange(-100000,100001)
            totals[g]=totals.get(g,0)+n
            counts[g]=counts.get(g,0)+1
            lines.append(g+","+str(Decimal(n)/100))
        result=group_csv_sum("\n".join(lines),"g","n")
        assert {r["group"]:Decimal(r["sum"])*100 for r in result["groups"]}==totals
        assert {r["group"]:r["count"] for r in result["groups"]}==counts


def test_transcript_search_retains_source_index_and_limits():
    records=[{"role":"user","text":"unrelated"},{"role":"tool","text":"CASE failed"},
             {"role":"tool","text":"case passed"}]
    r=search_transcript(records,"case",1)
    assert r["match_count"]==2 and r["truncated"]
    assert r["matches"]==[{"index":1,"role":"tool","text":"CASE failed"}]


def test_native_registration_and_real_handler_invocation():
    class Registry:
        def __init__(self):
            self.tools={}
        def register(self,name,description,handler):
            self.tools[name]=(description,handler)
    registry=Registry()
    register_portable_skills(registry)
    assert len(registry.tools)==4
    result=registry.tools["profile_csv"][1]({"text":"a\n1\n2"},"synthetic")
    assert result["row_count"]==2
    found=registry.tools["search_registered_skills"][1]({"query":"group csv sum"},"synthetic")
    assert found["matches"][0]["name"]=="group_csv_sum"
    assert found["execution_verified"] is False
