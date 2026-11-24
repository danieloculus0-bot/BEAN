"""Core client for the independently checked acquired-skill worker."""
import json
import math
import re
import socket

MAX=16384

class SkillCatalogClient:
    def __init__(self,path):
        self.path=path
    def request(self,payload):
        raw=json.dumps(payload,allow_nan=False).encode()+b"\n"
        if len(raw)>MAX:raise ValueError("request bounds")
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
            s.settimeout(15);s.connect(self.path);s.sendall(raw)
            with s.makefile("rb") as stream:reply=stream.readline(MAX+1)
        if len(reply)>MAX or not reply.endswith(b"\n"):raise ValueError("response bounds")
        row=json.loads(reply)
        if not isinstance(row,dict) or row.get("status")!="ok":raise ValueError("catalog worker rejected request")
        return row
    def list(self,args):
        if not isinstance(args,dict) or set(args)-{"kind","limit"} or args.get("kind") not in ("numeric","sequence"):raise ValueError("catalog kind")
        n=args.get("limit",12)
        if type(n) is not int or not 1<=n<=24:raise ValueError("limit")
        row=self.request({"op":"list","kind":args["kind"],"limit":n})
        if not isinstance(row.get("skills"),list) or len(row["skills"])>n:raise ValueError("catalog response")
        return row
    def execute(self,args):
        if not isinstance(args,dict) or set(args)!={"name","source_sha256","values"}:raise ValueError("skill contract")
        name=args["name"];sha=args["source_sha256"]
        if not isinstance(name,str) or not re.fullmatch(r"(derived|sequence)_[0-9a-f]{16}",name) or not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha):raise ValueError("identity")
        row=self.request({"op":"execute",**args})
        if row.get("name")!=name or row.get("source_sha256")!=sha or row.get("oracle_matched") is not True:raise ValueError("result identity or oracle")
        v=row.get("value")
        if name.startswith("sequence_"):
            if not isinstance(v,list) or len(v)>128 or any(type(x) is not int for x in v):raise ValueError("sequence output")
        elif type(v) not in (int,float) or not math.isfinite(v):raise ValueError("numeric output")
        return row

def register_skill_catalog(orchestrator,inbox,path):
    client=SkillCatalogClient(path)
    orchestrator.register("acquired_skill_catalog","Discover acquired skills by kind: {kind:numeric|sequence,limit?:int}. Returns name, expression, exact source_sha256.",lambda args,task_ref:client.list(args))
    orchestrator.register("execute_acquired_skill","Run retained code with oracle check: {name:str,source_sha256:str,values:[numbers]}. Use exact identity from acquired_skill_catalog.",lambda args,task_ref:client.execute(args))
    inbox.register("acquired_skill_catalog",lambda msg,session:client.list(msg.args))
    inbox.register("execute_acquired_skill",lambda msg,session:client.execute(msg.args))
