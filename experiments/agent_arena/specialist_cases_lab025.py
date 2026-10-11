"""Five independently scored, task-specific specialist challenges for Lab025.

Author stage imports public_case only. The sealed suites are consumed solely
by a separate credential-free GitHub job after authorship is complete.
"""
from __future__ import annotations
from hashlib import sha256
import json

CASES = {
"opencode": {
    "discipline": "repository API compatibility",
    "prompt": ("Repair candidate.py's resolve_endpoint(routes, request_path, method). "
        "routes is a list of dicts with path, methods, handler. Return handler of "
        "the first route whose path equals the request path after removing query "
        "string and fragment, normalizing repeated slashes and a single trailing "
        "slash, except root. Method comparisons are case-insensitive. Methods "
        "may be a string or a list of strings. If no route matches, return None. "
        "Do not mutate any input or add external dependencies."),
    "source": '''def resolve_endpoint(routes, request_path, method):
    for route in routes:
        if route["path"] == request_path and method in route["methods"]:
            return route["handler"]
    return None
''',
    "dev": '''import unittest
from candidate import resolve_endpoint as run
class Dev(unittest.TestCase):
    def test_query(self):
        self.assertEqual(run([{"path":"/orders","methods":["GET"],"handler":"A"}],"/orders?x=1","GET"),"A")
    def test_method(self):
        self.assertEqual(run([{"path":"/x","methods":"POST","handler":"B"}],"/x","post"),"B")
    def test_missing(self):
        self.assertIsNone(run([], "/missing", "GET"))
''',
    "holdout": '''import unittest
from candidate import resolve_endpoint as run
class Hidden(unittest.TestCase):
    def r(self,path,methods,handler): return {"path":path,"methods":methods,"handler":handler}
    def test_root(self): self.assertEqual(run([self.r("/","GET","root")],"//?v=2","get"),"root")
    def test_slashes(self): self.assertEqual(run([self.r("/api//jobs/","GET","ok")],"/api/jobs","GET"),"ok")
    def test_fragment(self): self.assertEqual(run([self.r("/a","get","A")],"/a#notes","GET"),"A")
    def test_only_first(self): self.assertEqual(run([self.r("/a","GET","first"),self.r("/a","GET","last")],"/a","GET"),"first")
    def test_method_list(self): self.assertEqual(run([self.r("/a",["PUT","PATCH"],"x")],"/a","patch"),"x")
    def test_string_method_is_single(self): self.assertIsNone(run([self.r("/a","GET","x")],"/a","E"))
    def test_empty(self): self.assertIsNone(run([], "/a","get"))
    def test_immutable(self):
        rows=[self.r("/a/","GET","x")]; before=[dict(r) for r in rows]
        run(rows,"/a","get"); self.assertEqual(rows,before)
'''
},
"goose": {
    "discipline": "manufacturing OTD and RMA reporting",
    "prompt": ("Repair summarize_shop(jobs, rmas, as_of). jobs contain id, due "
        "(YYYY-MM-DD), shipped (YYYY-MM-DD or None), and amount (nonnegative integer). "
        "Only jobs due on/before as_of are considered for OTD. A job is on time "
        "iff shipped exists and shipped <= due. Return dict keys due_count, "
        "on_time_count, otd_percent (rounded to 2 decimals; 100.0 if no jobs due), "
        "open_past_due (list of ids, sorted), and rma_units (sum of nonnegative "
        "integer units in rmas whose date <= as_of). Past-due means due < as_of "
        "and not yet shipped; exclude future due jobs. No input mutation or "
        "external dependencies."),
    "source": '''def summarize_shop(jobs, rmas, as_of):
    done = len(jobs)
    good = sum(bool(x.get("shipped")) for x in jobs)
    return {"due_count":done, "on_time_count":good,
            "otd_percent":good / done * 100 if done else 0,
            "open_past_due":[], "rma_units":len(rmas)}
''',
    "dev": '''import unittest
from candidate import summarize_shop as run
class Dev(unittest.TestCase):
    def test_otd(self):
        jobs=[dict(id="a",due="2026-10-10",shipped="2026-10-10",amount=1),
              dict(id="b",due="2026-10-09",shipped=None,amount=1)]
        self.assertEqual(run(jobs,[],"2026-10-10")["otd_percent"],50.0)
    def test_empty(self):
        self.assertEqual(run([],[],"2026-10-10")["otd_percent"],100.0)
    def test_rma(self):
        self.assertEqual(run([], [dict(date="2026-10-10",units=4)],"2026-10-10")["rma_units"],4)
''',
    "holdout": '''import unittest
from candidate import summarize_shop as run
class Hidden(unittest.TestCase):
    def job(self,i,d,s): return dict(id=i,due=d,shipped=s,amount=10)
    def test_future_due_ignored(self):
        a=run([self.job("a","2026-11-01",None)],[],"2026-10-10")
        self.assertEqual((a["due_count"],a["otd_percent"]),(0,100.0))
    def test_late_shipment_is_not_otd(self):
        a=run([self.job("x","2026-10-01","2026-10-02")],[],"2026-10-10")
        self.assertEqual(a["on_time_count"],0)
    def test_open_past_due_excludes_today(self):
        a=run([self.job("y","2026-10-10",None),self.job("x","2026-10-09",None)],[],"2026-10-10")
        self.assertEqual(a["open_past_due"],["x"])
    def test_open_past_due_sorted(self):
        a=run([self.job("z","2026-10-01",None),self.job("a","2026-10-02",None)],[],"2026-10-10")
        self.assertEqual(a["open_past_due"],["a","z"])
    def test_rma_cutoff(self):
        self.assertEqual(run([], [dict(date="2026-10-11",units=20)],"2026-10-10")["rma_units"],0)
    def test_rma_sum(self):
        self.assertEqual(run([], [dict(date="2026-10-09",units=2),dict(date="2026-10-10",units=7)],"2026-10-10")["rma_units"],9)
    def test_one_third(self):
        jobs=[self.job("a","2026-10-01","2026-10-01"),self.job("b","2026-10-01",None),self.job("c","2026-10-02",None)]
        self.assertEqual(run(jobs,[],"2026-10-10")["otd_percent"],33.33)
    def test_immutable(self):
        j=[self.job("a","2026-10-01",None)]; b=[dict(x) for x in j]
        run(j,[],"2026-10-10"); self.assertEqual(j,b)
'''
},
"openhands": {
    "discipline": "crash recovery and checkpoint replay",
    "prompt": ("Repair recover_state(records). Each record has job, sequence "
        "(nonnegative integer), state (string), valid (bool). For each job "
        "select the state from the greatest valid sequence, ignoring invalid "
        "records. If multiple valid records share sequence, prefer "
        "lexicographically smallest state. Return mapping job -> state, "
        "excluding jobs without valid checkpoints. Input may arrive in "
        "arbitrary order with duplicate records; no mutation."),
    "source": '''def recover_state(records):
    result={}
    for row in records:
        result[row["job"]]=row["state"]
    return result
''',
    "dev": '''import unittest
from candidate import recover_state as run
class Dev(unittest.TestCase):
    def test_max_seq(self):
        x=[dict(job="A",sequence=3,state="done",valid=True),
           dict(job="A",sequence=1,state="new",valid=True)]
        self.assertEqual(run(x)["A"],"done")
    def test_invalid(self):
        self.assertEqual(run([dict(job="A",sequence=1,state="bad",valid=False)]),{})
    def test_empty(self): self.assertEqual(run([]),{})
''',
    "holdout": '''import unittest
from candidate import recover_state as run
class Hidden(unittest.TestCase):
    def r(self,j,s,v=True,state="x"): return dict(job=j,sequence=s,state=state,valid=v)
    def test_highest_valid(self): self.assertEqual(run([self.r("a",10,False,"corrupt"),self.r("a",9,True,"safe")]),{"a":"safe"})
    def test_reverse(self):
        x=[self.r("a",1,state="old"),self.r("a",2,state="new")]
        self.assertEqual(run(x),run(x[::-1]))
    def test_repeated(self):
        x=self.r("a",2,state="same"); self.assertEqual(run([x,x,x]),{"a":"same"})
    def test_tie(self):
        self.assertEqual(run([self.r("a",2,state="z"),self.r("a",2,state="a")]),{"a":"a"})
    def test_tie_reverse(self):
        self.assertEqual(run([self.r("a",2,state="a"),self.r("a",2,state="z")]),{"a":"a"})
    def test_two_jobs(self):
        self.assertEqual(run([self.r("x",1,state="X"),self.r("y",2,state="Y")]),{"x":"X","y":"Y"})
    def test_no_valid(self): self.assertEqual(run([self.r("a",1,False)]),{})
    def test_immutable(self):
        x=[self.r("a",1)]; y=[dict(z) for z in x];run(x);self.assertEqual(x,y)
'''
},
"continue": {
    "discipline": "behavior-preserving deduplication refactor",
    "prompt": ("Repair unique_events(rows). Return a new list of records "
        "retaining the FIRST event for each key (device, sequence). Preserve "
        "original order and the dict values exactly. Rows may include "
        "extra data fields whose values are lists/dicts (unhashable). "
        "Do not mutate or replace caller dicts; output list must contain "
        "original record objects. Aim for O(n) expected runtime. "
        "A device may be an empty string; sequence may be zero."),
    "source": '''def unique_events(rows):
    return list({tuple(sorted(row.items())): row for row in rows}.values())
''',
    "dev": '''import unittest
from candidate import unique_events as run
class Dev(unittest.TestCase):
    def test_first(self):
        x=[dict(device="a",sequence=1,value=1),dict(device="a",sequence=1,value=2)]
        self.assertEqual(run(x),x[:1])
    def test_order(self):
        x=[dict(device="b",sequence=1),dict(device="a",sequence=1)]
        self.assertEqual(run(x),x)
    def test_empty(self): self.assertEqual(run([]),[])
''',
    "holdout": '''import unittest
from candidate import unique_events as run
class Hidden(unittest.TestCase):
    def test_nested_values(self):
        x=[dict(device="a",sequence=1,data={"list":[1,2]})]
        self.assertEqual(run(x),x)
    def test_first_object_identity(self):
        a=dict(device="a",sequence=1);b=dict(device="a",sequence=1)
        self.assertIs(run([a,b])[0],a)
    def test_different_seq(self):
        a=dict(device="a",sequence=0);b=dict(device="a",sequence=1)
        self.assertEqual(run([a,b]),[a,b])
    def test_different_device(self):
        a=dict(device="",sequence=1);b=dict(device="a",sequence=1)
        self.assertEqual(run([a,b]),[a,b])
    def test_preserve_order(self):
        x=[dict(device=x,sequence=1) for x in ("z","b","a")]
        self.assertEqual(run(x),x)
    def test_many(self):
        x=[dict(device=str(i%500),sequence=i//500) for i in range(10000)]
        self.assertEqual(len(run(x)),len(x))
    def test_same_key_with_extra(self):
        a=dict(device="a",sequence=1,v=0);b=dict(device="a",sequence=1,v=3)
        self.assertEqual(run([a,b]),[a])
    def test_empty(self): self.assertEqual(run([]),[])
'''
},
"cline": {
    "discipline": "deny-wins transitive access control",
    "prompt": ("Repair can_access(user, action, memberships, grants, denies). "
        "memberships maps principals to parent-group lists and can contain "
        "cycles. grants and denies map principals to action-name lists. "
        "A reachable DENY anywhere, including indirect group parents, "
        "overrides every grant. A grant anywhere reachable permits otherwise. "
        "Unknown actions default to False. Preserve public signature and "
        "never mutate the input graph."),
    "source": '''def can_access(user, action, memberships, grants, denies):
    if action in grants.get(user, []):
        return True
    return any(action in grants.get(g,[]) for g in memberships.get(user,[]))
''',
    "dev": '''import unittest
from candidate import can_access as run
class Dev(unittest.TestCase):
    def test_direct(self): self.assertTrue(run("a","read",{},{"a":["read"]},{}))
    def test_deny(self): self.assertFalse(run("a","read",{},{"a":["read"]},{"a":["read"]}))
    def test_group(self): self.assertTrue(run("a","read",{"a":["g"]},{"g":["read"]},{}))
''',
    "holdout": '''import unittest
from candidate import can_access as run
class Hidden(unittest.TestCase):
    def test_transitive_grant(self):
        self.assertTrue(run("a","read",{"a":["g"],"g":["parent"]},{"parent":["read"]},{}))
    def test_transitive_deny(self):
        self.assertFalse(run("a","read",{"a":["g"],"g":["p"]},{"a":["read"]},{"p":["read"]}))
    def test_cycle(self):
        self.assertTrue(run("a","read",{"a":["g"],"g":["a"]},{"g":["read"]},{}))
    def test_deny_branch(self):
        self.assertFalse(run("a","read",{"a":["g","h"]},{"g":["read"]},{"h":["read"]}))
    def test_missing(self): self.assertFalse(run("a","write",{},{"a":["read"]},{}))
    def test_direct_deny(self): self.assertFalse(run("a","read",{},{"a":["read"]},{"a":["read"]}))
    def test_negative_indirect(self):
        self.assertFalse(run("a","read",{"a":["g"],"g":["p"]},{"g":["read"]},{"p":["read"]}))
    def test_immutable(self):
        m={"a":["g"]};b={k:list(v) for k,v in m.items()};run("a","read",m,{},{});self.assertEqual(m,b)
'''
},
}

def public_case(name):
    if name not in CASES:
        raise ValueError("unknown opponent")
    item = CASES[name]
    return {"name":name,"prompt":item["prompt"],"source":item["source"],
            "source_sha256":sha256(item["source"].encode()).hexdigest(),
            "discipline":item["discipline"]}

def digest():
    return {name: {"public": sha256(json.dumps(public_case(name),sort_keys=True).encode()).hexdigest(),
                   "holdout":sha256(item["holdout"].encode()).hexdigest(),
                   "development":sha256(item["dev"].encode()).hexdigest()}
            for name,item in CASES.items()}
