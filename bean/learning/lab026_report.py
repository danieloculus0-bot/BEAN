"""Run Lab026 reproducible mechanism smoke, exporting transparent receipts.

Synthetic fixture shows correct wiring; it must never be called real LLM
learning. Real Ollama trials require explicit CLI and evaluator task files
owned by the operator, not included in model prompts.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile

from .experimental import Lesson,TrialCase,ExperienceBank,assess_nodes,run_paired_trial
from .bridge import bridge_contract


class SyntheticModel:
    model_id="synthetic-fixture-sorting-v1"
    provider_kind="synthetic_fixture"

    def complete(self,question,context):
        if "SORT_ASC" in context and question.startswith("sort "):
            return ",".join(sorted(question[5:].split(",")))
        return "unknown"


def smoke(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    file=output/"adaptive-lab026.sqlite"
    bank=ExperienceBank(file)
    try:
        for index,(strategy,text) in enumerate([
            ("reflection","SORT_ASC"),
            ("skill","SORT_ASC"),
            ("prompt","SORT_ASC"),
        ]):
            bank.add(Lesson(strategy+"-1",strategy,"sorting",text,
                            ("synthetic:known-failure:"+str(index),),
                            "Synthetic baseline failed to sort"))
        bank.add(Lesson("placebo-1","reflection","welding","MIG_WELD",
                        ("synthetic:unrelated-fixture",),"Unrelated domain"))
        cases=[TrialCase("s1","sorting","sort c,a,b","a,b,c"),
               TrialCase("s2","sorting","sort z,y","y,z"),
               TrialCase("s3","sorting","sort e,d","d,e")]
        experiment=run_paired_trial(
            bank=bank,cases=cases,model=SyntheticModel(),
            judge=lambda expected,actual:expected==actual,
            context_chars=200,replicates=2,
        )
        bridge=bridge_contract()
        result={
            "schema":"bean.adaptive_lab026.smoke.v1",
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "nodes":assess_nodes(bridge_available=bridge["bridge_available"]),
            "bridge_contract":bridge,
            "trial":experiment,
            "interpretation":"Synthetic mechanism and persistence demonstration, not measured new model learning",
        }
        (output/"mechanism_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
        bank.close()
        restored=ExperienceBank(file)
        try:
            result["restart_verified"]=len(restored.lessons())==4
            if not result["restart_verified"]:
                raise ValueError("Restart did not recover all lessons")
            restored.journal.verify()
        finally:
            restored.close()
        (output/"mechanism_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
        lines=[
            "# BEAN Lab026 — Experimental Adaptive Learning Node Viability",
            "",
            "This smoke uses a SYNTHETIC FIXTURE. No neural model was trained or improved.",
            "",
            "| Node | Source dependency | Independent learning proof |",
            "|---|---|---|",
        ]
        for item in result["nodes"]:
            lines.append("| "+item["node"]+" | "+
                         ("present" if item["dependency_present"] else "missing/research")+" | no |")
        lines.extend(["","## Control-arm test","",
                      "A deliberately simple fixture knows how to sort only when a",
                      "supplied context includes an explicit rule. This validates",
                      "experimental wiring, not generalized learning.","",
                      "| Arm | Synthetic successes |","|---|---:|"])
        for arm,value in experiment["scores"].items():
            lines.append("| "+arm+" | "+str(value)+" / "+
                         str(experiment["cases"]*experiment["replicates"])+" |")
        lines.extend(["",
            "The provider is labeled synthetic_fixture. Sealed test labels are",
            "held by the local evaluator, not sent as a model input.",
            "The source-hash journal was reopened after restart.",
            "Bridge source import status: "+str(bridge["bridge_available"])+".",
            "Real provider experiments, cross-domain transfer, model training,",
            "independent source authentication and proof of growth remain unproven."])
        (output/"VIABILITY.md").write_text("\n".join(lines)+"\n")
        return result
    finally:
        try:
            bank.close()
        except Exception:
            pass


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="lab026-evidence")
    args=p.parse_args()
    smoke(args.output)
    print((Path(args.output)/"VIABILITY.md").read_text())


if __name__=="__main__":
    main()
