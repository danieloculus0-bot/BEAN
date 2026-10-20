"""Lab026 live local Ollama feedback -> persisted strategy -> unseen evaluation.

Training labels are explicitly allowed in the *development* feedback only.
Holdout truths are never included in model prompts. This is prompted strategy
learning, not gradient/weight learning; no production code is modified.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .experimental import ExperienceBank,Lesson,TrialCase,run_paired_trial
from .model_adapters import LocalOllamaTrialModel


def _load(file,expected_schema):
    p=Path(file)
    data=json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema")!=expected_schema or not isinstance(data.get("cases"),list):
        raise ValueError("Experiment requires a versioned cases JSON")
    if len(data["cases"])<2:
        raise ValueError("At least two real example cases required")
    return data


def _feedback_questions(cases,domain):
    lines=[]
    for item in cases:
        if item["domain"]!=domain:
            continue
        for key in ("id","question","expected","observed","evidence_ref"):
            if not isinstance(item.get(key),str) or not item[key].strip():
                raise ValueError("Development feedback missing original evidence")
        lines.append({
            "question":item["question"],"model_answer":item["observed"],
            "correct_answer":item["expected"],"source":item["evidence_ref"],
        })
    if not lines:
        raise ValueError("Domain lacks supervised development examples")
    return lines


def create_strategy_lessons(bank,model,development,domain):
    """Ask the same real model for three alternative transferable hypotheses."""
    pairs=_feedback_questions(development["cases"],domain)
    refs=tuple(sorted(set(row["source"] for row in pairs)))
    fingerprint=sha256(json.dumps(pairs,sort_keys=True).encode()).hexdigest()[:14]
    kinds={
        "reflection":"Infer a brief transferable error-correction rule from mistakes.",
        "skill":"Propose a reusable task-solving procedure, not memorized answers.",
        "prompt":"Optimize a short instruction for reliability and concise answers.",
    }
    created=[]
    for strategy,instruction in kinds.items():
        lesson_id="lab026:"+fingerprint+":"+strategy
        if any(x.lesson_id==lesson_id for x in bank.lessons()):
            created.append(lesson_id)
            continue
        # Development examples supplied here are NEVER holdout examples.
        question=(instruction+
          " Do not claim results you did not see. Use these development examples: "+
          json.dumps(pairs,ensure_ascii=False))
        result=model.complete(question,"")
        if not result.strip():
            raise ValueError("Reflection provider returned empty candidate")
        new=Lesson(lesson_id,strategy,domain,result[:4000],refs,
                   "model-proposed hypothesis from labeled development examples")
        bank.add(new)
        created.append(lesson_id)
    return created


def run_local_trial(*,development_path,holdout_path,output,domain,
                    model_name="qwen2.5-coder:1.5b",replicates=2):
    development=_load(development_path,"bean.lab026.development.v1")
    holdout=_load(holdout_path,"bean.lab026.holdout.v1")
    dev_ids={item["id"] for item in development["cases"]}
    hold_ids=[item.get("id") for item in holdout["cases"]]
    if not all(isinstance(x,str) for x in hold_ids) or \
       len(set(hold_ids))!=len(hold_ids) or dev_ids.intersection(hold_ids):
        raise ValueError("Holdout and development task identities must not overlap")
    cases=[TrialCase(item["id"],item["domain"],item["question"],item["expected"])
           for item in holdout["cases"]]
    if not all(c.domain==domain for c in cases):
        raise ValueError("Single-domain matched comparison requires same-domain holdouts")
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    model=LocalOllamaTrialModel(model_name)
    bank=ExperienceBank(output/"persistent_adaptive_ledger.sqlite")
    try:
        created=create_strategy_lessons(bank,model,development,domain)
        # Caller may supply irrelevant-domain placebo lessons from a separate
        # trial; absence is explicitly reported, not treated as valid placebo.
        has_placebo=bool([x for x in bank.lessons(strategy="reflection")
                          if x.domain!=domain])
        receipt=run_paired_trial(bank=bank,cases=cases,model=model,
             judge=lambda expected,answer:expected.strip()==answer.strip(),
             replicates=replicates)
        receipt["placebo_context_present"]=has_placebo
        receipt["lesson_ids"]=created
        receipt["holdout_task_ids"]=hold_ids
        receipt["limitation"]="Exact-match host evaluator and public task set; no blind external judge or weight update."
        receipt["learning_proven"]=False
        (output/"local_ollama_experiment.json").write_text(
            json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
        return receipt
    finally:
        bank.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--development",required=True)
    p.add_argument("--holdout",required=True)
    p.add_argument("--domain",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--model",default="qwen2.5-coder:1.5b")
    p.add_argument("--replicates",type=int,default=2)
    a=p.parse_args()
    result=run_local_trial(development_path=a.development,holdout_path=a.holdout,
             output=a.out,domain=a.domain,model_name=a.model,replicates=a.replicates)
    print(json.dumps({k:v for k,v in result.items() if k not in ("records",)},
                     indent=2))


if __name__=="__main__":
    main()
