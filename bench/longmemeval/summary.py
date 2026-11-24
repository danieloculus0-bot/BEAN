"""Summarize only complete provenance-bearing JSONL observations."""
import argparse,json
from collections import defaultdict
from pathlib import Path

def summarize(paths):
    groups=defaultdict(list)
    seen=set()
    identity=None
    for path in paths:
        for line in Path(path).read_text().splitlines():
            row=json.loads(line)
            for field in ("study_id","commit_sha","run_id","artifact","model_digest","judge_digest","dataset_sha256","subset"):
                if not row.get(field):
                    raise ValueError("UNVERIFIED: missing "+field)
            scope=tuple(row[k] for k in ("study_id","model_digest","judge_digest","dataset_sha256","subset"))
            if identity is None:
                identity=scope
            if scope!=identity:
                raise ValueError("incompatible study conditions")
            key=(row["arm"],row["question_id"])
            if key in seen:
                raise ValueError("duplicate observation")
            seen.add(key)
            if type(row["judge_verdict"]) is not bool:
                raise ValueError("invalid judge label")
            groups[row["arm"]].append(row)
    return {arm:{"n":len(rows),"accuracy":sum(r["judge_verdict"] for r in rows)/len(rows),
                 "avg_context_tokens":sum(r["context_tokens"] for r in rows)/len(rows),
                 "receipts":sorted({(r["commit_sha"],r["run_id"],r["artifact"]) for r in rows})}
            for arm,rows in sorted(groups.items())}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("jsonl",nargs="+")
    print(json.dumps(summarize(p.parse_args().jsonl),indent=2))
