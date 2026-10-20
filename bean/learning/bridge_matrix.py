"""Cross-platform Lab026 node receipt comparison via ACTUAL BEAN AI Bridge.

Linux and Windows are separate executed runners, but they share code and
fixtures. This is reproducibility of mechanisms, not independent factual
authentication or evidence that an LLM has learned.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path

from .bridge import audit_sources
from .experimental import NODES


def compare_node_receipts(linux_path,windows_path,output):
    from ezbean.learning_loop import SourceObservation

    inputs={}
    for name,path in (("linux",Path(linux_path)),("windows",Path(windows_path))):
        raw=path.read_bytes()
        data=json.loads(raw)
        if data.get("schema")!="bean.adaptive_lab026.smoke.v1":
            raise ValueError("Expected actual Lab026 mechanism receipt")
        if data.get("restart_verified") is not True or \
           data.get("trial",{}).get("verdict")!="synthetic_fixture_not_learning_proof":
            raise ValueError("Incomplete or mislabeled native source evidence")
        found={n["node"]:n for n in data["nodes"]}
        if set(found)!=set(NODES):
            raise ValueError("Missing node in source evidence")
        inputs[name]={"data":data,"nodes":found,
                      "sha":sha256(raw).hexdigest()}
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    audited=[]
    class ReproducibilityVerifier:
        def __init__(self,node,value):
            self.node=node
            self.value=value
        def check(self,concept,source):
            side=source.origin
            if side not in inputs or not source.ref.endswith(inputs[side]["sha"]):
                return False
            report=inputs[side]["nodes"][self.node]
            return (report["viability"]==self.value and
                    report["origin_values_unchanged"] is True and
                    report["learning_improvement_verified"] is False)
    class AbstainingModel:
        def complete(self,payload):
            return {"message":{"content":json.dumps({
                "concept":payload["requested_concept"],
                "decision":"abstain","value":None,"definition_ids":[]})}}
    for node in NODES:
        first=inputs["linux"]["nodes"][node]
        second=inputs["windows"]["nodes"][node]
        same=(first["viability"]==second["viability"] and
              first["dependency_present"]==second["dependency_present"])
        if not same:
            audited.append({"node":node,"outcome":"cross_platform_disagreement",
                            "bridge_outcome":None})
            continue
        value=first["viability"]
        sources=[
            SourceObservation("receipt:linux:"+inputs["linux"]["sha"],
                              "linux",value),
            SourceObservation("receipt:windows:"+inputs["windows"]["sha"],
                              "windows",value),
        ]
        result=audit_sources(
            db_path=str(output/(node+".sqlite")),
            concept="lab026_"+node,
            as_of="2026-10-20T23:00:00Z",
            observations=sources,verifier=ReproducibilityVerifier(node,value),
            provider=AbstainingModel())
        outcome=result["outcome"]
        if (outcome["system_answer"]!=value or
                outcome["distinct_origins"]!=2 or
                outcome["investigation_status"]!="committed_verified_revision"):
            raise ValueError("Real Bridge failed two-source node reproducibility check")
        audited.append({"node":node,"outcome":"cross_platform_mechanism_reproduced",
                        "viability":value,"bridge_outcome":outcome["investigation_status"],
                        "learning_improvement_verified":False,
                        "provenance":"Windows/Linux synthetic mechanism receipts, not independent factual truth"})
    report={
        "schema":"bean.lab026.bridge_matrix.v1",
        "source_sha256":{side:item["sha"] for side,item in inputs.items()},
        "nodes":audited,
        "learning_demonstrated":False,
        "bridge_used":"real ezbean.learning_loop.EvidenceLearningLoop",
        "caveat":"Bridge verifier attests executed CI receipt reproducibility, not natural-language or physics truth",
    }
    (output/"bridge_node_viability.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# BEAN Lab026 real-Bridge per-node viability", "",
           "Two separate operating-system jobs produced native evidence. Actual",
           "BEAN AI Bridge checked hashed receipts and required agreement.",
           "This is NOT independent demonstration of model learning.",
           "",
           "| Node | Source status | Cross-platform result | Causal growth proven |",
           "|---|---|---|---|"]
    for node in audited:
        lines.append("| "+node["node"]+" | "+node.get("viability","disagreed")+
                     " | "+node["outcome"]+" | no |")
    lines.extend(["",
        "The upstream BEAN plugin screened proposals using heuristic source rules.",
        "Its hosted JavaScript adapter cannot run the Python Core or verify learning.",
        "Weight learning has no implementation in this experiment; source checks",
        "cannot establish its actual feasibility or test performance."])
    (output/"BRIDGE_NODE_MATRIX.md").write_text("\n".join(lines)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--linux",required=True)
    p.add_argument("--windows",required=True)
    p.add_argument("--output",default="lab026-bridge-matrix")
    a=p.parse_args()
    compare_node_receipts(a.linux,a.windows,a.output)
    print((Path(a.output)/"BRIDGE_NODE_MATRIX.md").read_text())


if __name__=="__main__":
    main()
