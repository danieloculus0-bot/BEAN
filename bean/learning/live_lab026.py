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
from .strategy_selection import choose_strategy


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


def _fingerprints(cases):
    """Protect against differently named duplicates crossing data partitions."""
    ids = set()
    questions = set()
    for item in cases:
        ident, domain, question = item.get("id"), item.get("domain"), item.get("question")
        if not all(isinstance(x, str) and x.strip() for x in (ident, domain, question)):
            raise ValueError("Each task requires id, domain and question")
        if ident in ids:
            raise ValueError("Task identifiers must be distinct")
        ids.add(ident)
        questions.add((domain.strip().casefold(), " ".join(question.split()).casefold()))
    return ids, questions


def run_local_trial(*,development_path,holdout_path,output,domain,
                    model_name="qwen2.5-coder:1.5b",replicates=2,
                    selection_path=None):
    development=_load(development_path,"bean.lab026.development.v1")
    holdout=_load(holdout_path,"bean.lab026.holdout.v1")
    selection=(_load(selection_path,"bean.lab026.selection.v1")
               if selection_path is not None else None)
    dev_ids,dev_questions=_fingerprints(development["cases"])
    hold_ids,hold_questions=_fingerprints(holdout["cases"])
    if dev_ids & hold_ids or dev_questions & hold_questions:
        raise ValueError("Holdout and development tasks must not overlap")
    if selection is not None:
        select_ids,select_questions=_fingerprints(selection["cases"])
        if (select_ids & (dev_ids | hold_ids) or
                select_questions & (dev_questions | hold_questions)):
            raise ValueError("Selection tasks must be distinct from development and holdout")
    cases=[TrialCase(item["id"],item["domain"],item["question"],item["expected"])
           for item in holdout["cases"]]
    if not all(c.domain==domain for c in cases):
        raise ValueError("Single-domain matched comparison requires same-domain holdouts")
    if selection is not None and not all(x["domain"]==domain for x in selection["cases"]):
        raise ValueError("Selection cases must have the target domain")

    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    model=LocalOllamaTrialModel(model_name)
    db=output/"persistent_adaptive_ledger.sqlite"
    bank=ExperienceBank(db)
    try:
        created=create_strategy_lessons(bank,model,development,domain)
        # Generate truly unrelated domain lessons only when evidence for
        # that domain was supplied in the development file.
        other_domains=sorted({x["domain"] for x in development["cases"]}-{domain})
        for other_domain in other_domains:
            created.extend(create_strategy_lessons(bank,model,development,other_domain))
        has_placebo=bool([x for x in bank.lessons(strategy="reflection")
                          if x.domain!=domain])
        selection_trial=None
        chosen=None
        restart_policy_verified=False
        if selection is not None:
            if not has_placebo:
                raise ValueError("Selection comparison requires unrelated-domain placebo data")
            selection_cases=[
                TrialCase(item["id"],item["domain"],item["question"],item["expected"])
                for item in selection["cases"]
            ]
            selection_trial=run_paired_trial(
                bank=bank,cases=selection_cases,model=model,
                judge=lambda expected,answer: expected.strip()==answer.strip(),
                arms=("cold","reflection","skill","prompt","placebo"),
                replicates=replicates)
            chosen=choose_strategy(bank,selection_trial,domain)
            bank.close()
            bank=ExperienceBank(db)
            restart_policy_verified=(bank.selected_arm(domain)==chosen["arm"])
            if not restart_policy_verified:
                raise ValueError("Learned selection failed restart replay")
        final_arms=("cold","reflection","skill","prompt","placebo","adaptive") \
            if selection is not None else ("cold","reflection","skill","prompt","placebo")
        trial=run_paired_trial(bank=bank,cases=cases,model=model,
             judge=lambda expected,answer:expected.strip()==answer.strip(),
             arms=final_arms,replicates=replicates)
        report={
            "schema":"bean.lab026.real_trial_envelope.v1",
            "selection_trial_receipt":selection_trial,
            "selected_strategy":chosen,
            "selection_survived_restart":restart_policy_verified,
            "trial_receipt":trial,
            "placebo_context_present":has_placebo,
            "lesson_ids":created,
            "holdout_task_ids":[x["id"] for x in holdout["cases"]],
            "limitation":"Exact-match host judge. Model and prompt strategy are tested, not trained weights; no independent blind evaluator.",
            "learning_proven":False,
        }
        (output/"local_ollama_experiment.json").write_text(
            json.dumps(report,indent=2)+"\n",encoding="utf-8")
        return report
    finally:
        bank.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--development",required=True)
    p.add_argument("--holdout",required=True)
    p.add_argument("--selection",default=None,
                   help="Separate validation set for measured adaptive strategy choice")
    p.add_argument("--domain",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--model",default="qwen2.5-coder:1.5b")
    p.add_argument("--replicates",type=int,default=2)
    a=p.parse_args()
    result=run_local_trial(development_path=a.development,holdout_path=a.holdout,
             output=a.out,domain=a.domain,model_name=a.model,replicates=a.replicates,
             selection_path=a.selection)
    print(json.dumps({"scores":result["trial_receipt"]["scores"],
                      "model_id":result["trial_receipt"]["model_id"],
                      "placebo_context_present":result["placebo_context_present"],
                      "learning_proven":result["learning_proven"],
                      "selected_arm":(result["selected_strategy"] or {}).get("arm"),
                      "selection_survived_restart":result["selection_survived_restart"]},indent=2))


if __name__=="__main__":
    main()
