"""Discover and execute retained lab acquisitions via a bounded typed protocol.

Worker only: model-written source runs in a separate OS-isolated service.
Every returned value is checked against a host-authored reference evaluator.
Lab metadata is a candidate claim, not authority to execute arbitrary code.
"""
import ast
import hashlib
import json
import math
import operator
import re
import sqlite3
import sys
from pathlib import Path

from bean.optimization.autodev import canonical

SHA=re.compile(r"[0-9a-f]{64}")
NAME=re.compile(r"(?:derived|sequence)_[0-9a-f]{16}")
MAX=16384
SEQ={
    "reverse":lambda v:v[::-1],"ascending":sorted,
    "descending":lambda v:sorted(v,reverse=True),
    "even":lambda v:[x for x in v if x%2==0],
    "positive":lambda v:[x for x in v if x>0],
    "nonzero":lambda v:[x for x in v if x!=0],
    "absolute":lambda v:[abs(x) for x in v],
    "first_occurrence":lambda v:list(dict.fromkeys(v)),
    "adjacent_difference":lambda v:[b-a for a,b in zip(v,v[1:])],
    "even_positions":lambda v:v[::2],"odd_positions":lambda v:v[1::2],
    "prefix_three":lambda v:v[:3],"suffix_three":lambda v:v[-3:],
}
NUM={"min":min,"max":max,"sum":math.fsum,
     "mean":lambda v:math.fsum(v)/len(v),
     "span":lambda v:max(v)-min(v),
     "energy":lambda v:math.fsum(x*x for x in v),
     "variance":lambda v:math.fsum((x-math.fsum(v)/len(v))**2 for x in v)/len(v),
     "rms":lambda v:math.sqrt(math.fsum(x*x for x in v)/len(v))}
OPS={"add":operator.add,"sub":operator.sub,"mul":operator.mul,"div":operator.truediv}
BUILTINS={x:getattr(__import__("builtins"),x) for x in
          ("sum","len","min","max","abs","round","float","int","range","sorted","enumerate","zip","pow","list","set")}
ALLOWED=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Return,
         ast.Assign,ast.AugAssign,ast.Expr,ast.Name,ast.Load,ast.Store,
         ast.Constant,ast.BinOp,ast.UnaryOp,ast.Add,ast.Sub,ast.Mult,ast.Div,
         ast.Pow,ast.Mod,ast.FloorDiv,ast.USub,ast.UAdd,ast.Call,ast.keyword,
         ast.List,ast.Tuple,ast.Subscript,ast.Slice,ast.GeneratorExp,ast.ListComp,
         ast.comprehension,ast.For,ast.If,ast.IfExp,ast.Compare,ast.Eq,ast.NotEq,
         ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.BoolOp,ast.And,ast.Or,ast.Not,ast.Pass,
         ast.Break,ast.Continue,ast.In,ast.NotIn,ast.Set,ast.SetComp)

def numeric_terms(expr,depth=0):
    if depth>3:raise ValueError("depth")
    if isinstance(expr,str) and expr in NUM:return {expr}
    if not isinstance(expr,list) or len(expr)!=3 or not isinstance(expr[0],str) or expr[0] not in OPS:raise ValueError("expression")
    return numeric_terms(expr[1],depth+1)|numeric_terms(expr[2],depth+1)

def validate_expression(kind,expr):
    if kind=="sequence":
        if not isinstance(expr,list) or not 2<=len(expr)<=4 or any(type(x) is not str or x not in SEQ for x in expr) or len(set(expr))<2:raise ValueError("sequence expression")
    elif kind=="numeric":
        if len(numeric_terms(expr))<2:raise ValueError("numeric expression")
    else:raise ValueError("kind")

def oracle(kind,expr,values):
    validate_expression(kind,expr)
    if not isinstance(values,list) or len(values)>128:raise ValueError("input size")
    if kind=="sequence":
        if any(type(x) is not int or abs(x)>10**8 for x in values):raise ValueError("integer values")
        out=list(values)
        for op in expr:out=SEQ[op](out)
        return out
    if not values or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<x<=1e6 for x in values):raise ValueError("positive finite values")
    def run(e):
        return NUM[e](values) if isinstance(e,str) else OPS[e[0]](run(e[1]),run(e[2]))
    result=run(expr)
    if not math.isfinite(result):raise ValueError("undefined result")
    return result

def source_function(source):
    if not isinstance(source,str) or len(source)>12000:raise ValueError("source size")
    tree=ast.parse(source)
    body=[n for n in tree.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))]
    if len(body)!=1 or not isinstance(body[0],ast.FunctionDef):raise ValueError("one function required")
    f=body[0];a=f.args
    if f.name!="solve" or f.decorator_list or f.returns or a.posonlyargs or len(a.args)!=1 or a.args[0].annotation or a.defaults or a.vararg or a.kwarg or a.kwonlyargs:raise ValueError("invalid signature")
    for n in ast.walk(tree):
        if not isinstance(n,ALLOWED):raise ValueError("unsupported AST")
        if isinstance(n,ast.Name) and (n.id.startswith("_") or (isinstance(n.ctx,ast.Store) and n.id in BUILTINS)):raise ValueError("invalid name")
        if isinstance(n,ast.Call) and (not isinstance(n.func,ast.Name) or n.func.id not in BUILTINS):raise ValueError("invalid call")
        if isinstance(n,ast.comprehension) and n.is_async:raise ValueError("async")
    # This is NOT an OS sandbox; only the isolated worker may invoke it.
    scope={"__builtins__":dict(BUILTINS)}
    exec(compile(tree,"<retained-lab-skill>","exec"),scope)
    return scope["solve"]

def catalog(root,kind):
    if kind not in ("numeric","sequence"):raise ValueError("kind")
    root=Path(root)
    journal=root/("dynamic_cycles.jsonl" if kind=="numeric" else "sequence_cycles.jsonl")
    if not journal.exists():return []
    if journal.is_symlink() or journal.stat().st_size>8*1024*1024:raise ValueError("journal bounds")
    rows={}
    with journal.open() as stream:
        for line in stream:
            if len(line)>32768:continue
            try:
                r=json.loads(line)
                if r.get("passed") is not True or r.get("acquisition_passed") is not True:continue
                if r.get("transfer",{}).get("passed") is not True or r.get("transfer",{}).get("fresh_process") is not True:continue
                if type(r.get("transfer_count")) is not int or r["transfer_count"]<12:continue
                name=r["skill"];expr=r["expression"];sha=r["candidate_sha256"];objective=r["objective_sha256"]
                validate_expression(kind,expr)
                prefix="derived_" if kind=="numeric" else "sequence_"
                if name!=prefix+hashlib.sha256(canonical(expr)).hexdigest()[:16]:continue
                if not SHA.fullmatch(sha) or not SHA.fullmatch(objective) or r["transfer"].get("source_sha256")!=sha:continue
                rows[(name,sha)]={"name":name,"kind":kind,"expression":expr,"source_sha256":sha,"objective_sha256":objective,"transfer_count":r["transfer_count"]}
            except (ValueError,KeyError,TypeError,AttributeError):continue
    return list(rows.values())

def read_source(root,entry):
    db=Path(root)/"verified_skills.sqlite"
    if db.is_symlink() or not db.is_file():raise ValueError("skill database")
    with sqlite3.connect(db.resolve().as_uri()+"?mode=ro",uri=True,timeout=2) as c:
        rows=c.execute("SELECT source,sha256 FROM verified_skills WHERE name=? AND objective=?",
                       (entry["name"],entry["objective_sha256"])).fetchall()
    if len(rows)!=1:raise ValueError("ambiguous source")
    source,sha=rows[0]
    if sha!=entry["source_sha256"] or hashlib.sha256(source.encode()).hexdigest()!=sha:raise ValueError("source digest")
    return source

def dispatch(root,request):
    if not isinstance(request,dict):raise ValueError("request")
    if request.get("op")=="list" and set(request)=={"op","kind","limit"}:
        n=request["limit"]
        if type(n) is not int or not 1<=n<=24:raise ValueError("limit")
        entries=[]
        for e in reversed(catalog(root,request["kind"])):
            try:read_source(root,e)
            except (ValueError,sqlite3.Error):continue
            entries.append(e)
            if len(entries)>=n:break
        return {"status":"ok","skills":entries,"count":len(entries),"catalog_scope":"retained_candidate_receipts"}
    if request.get("op")!="execute" or set(request)!={"op","name","source_sha256","values"}:raise ValueError("contract")
    name=request["name"];sha=request["source_sha256"]
    if not isinstance(name,str) or not NAME.fullmatch(name) or not isinstance(sha,str) or not SHA.fullmatch(sha):raise ValueError("skill identity")
    kind="sequence" if name.startswith("sequence_") else "numeric"
    entries=[e for e in catalog(root,kind) if e["name"]==name and e["source_sha256"]==sha]
    if len(entries)!=1:raise ValueError("candidate not retained")
    e=entries[0];values=request["values"]
    expected=oracle(kind,e["expression"],values)
    copied=list(values)
    result=source_function(read_source(root,e))(copied)
    if copied!=values:raise ValueError("mutated input")
    if kind=="sequence":
        match=type(result) is list and all(type(x) is int for x in result) and result==expected
    else:
        match=type(result) in (int,float) and math.isfinite(result) and math.isclose(result,expected,rel_tol=1e-9,abs_tol=1e-9)
    if not match:raise ValueError("independent oracle mismatch")
    return {"status":"ok","name":name,"kind":kind,"source_sha256":sha,
            "value":result,"oracle_matched":True,"scope":"host_defined_grammar"}

def main():
    # Fixed host-controlled location; request never chooses a path.
    try:
        raw=sys.stdin.buffer.readline(MAX+1)
        if len(raw)>MAX or not raw.endswith(b"\n"):raise ValueError("request bounds")
        reply=dispatch("/var/lib/bean-lab",json.loads(raw))
        data=canonical(reply)
        if len(data)>MAX:raise ValueError("reply bounds")
        sys.stdout.buffer.write(data+b"\n");sys.stdout.buffer.flush()
    except Exception as e:
        print(json.dumps({"status":"error","error_class":type(e).__name__}),flush=True)

if __name__=="__main__":main()
