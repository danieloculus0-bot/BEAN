"""Independently implemented portable data skills for BEAN's native planner.

Design reference: https://docs.openclaw.ai/tools/skills
No upstream code copied; no external command execution or filesystem access.
"""
import csv
import io
import re
from collections import Counter
from decimal import Decimal, InvalidOperation

MAX_CHARS = 64000
MAX_ROWS = 1000


def _string(value, limit=MAX_CHARS):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("expected bounded text")
    return value


def _table(text):
    reader = csv.DictReader(io.StringIO(_string(text), newline=""), strict=True)
    fields = reader.fieldnames
    if not fields or len(fields) > 64 or any(not x.strip() for x in fields) or len(set(fields)) != len(fields):
        raise ValueError("invalid or duplicate CSV headers")
    rows = []
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("ragged CSV row")
        if len(rows) >= MAX_ROWS:
            raise ValueError("CSV row limit exceeded")
        rows.append(row)
    return fields, rows


def profile_csv(text):
    fields, rows = _table(text)
    columns = {}
    for field in fields:
        values = [r[field] for r in rows if r[field].strip()]
        columns[field] = {"present": len(values), "missing": len(rows)-len(values),
                          "distinct": len(set(values))}
    return {"row_count": len(rows), "columns": columns}


def group_csv_sum(text, group, value):
    fields, rows = _table(text)
    if group not in fields or value not in fields:
        raise ValueError("unknown group or value column")
    sums = {}
    counts = Counter()
    for row in rows:
        key = row[group]
        try:
            raw = Decimal(row[value])
        except InvalidOperation as exc:
            raise ValueError("non-numeric value") from exc
        if not raw.is_finite() or len(raw.as_tuple().digits)>24 or not -12 <= raw.as_tuple().exponent <= 12:
            raise ValueError("numeric value outside bounded decimal range")
        sign, digits, exp = raw.as_tuple()
        scaled = int("".join(map(str,digits))) * 10**(exp+12)
        sums[key] = sums.get(key,0) + (-scaled if sign else scaled)
        counts[key] += 1

    def format_scaled(n):
        integer, fraction = divmod(abs(n), 10**12)
        suffix = ("%012d" % fraction).rstrip("0")
        return ("-" if n < 0 else "") + str(integer) + ("." + suffix if suffix else "")

    return {"groups": [{"group":key,"count":counts[key],"sum":format_scaled(sums[key])}
                        for key in sorted(sums)], "row_count":len(rows)}


def search_transcript(records, query, limit=10):
    query = _string(query,256).strip().casefold()
    if not query or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("nonempty query and limit 1..20 required")
    if not isinstance(records,list) or len(records)>MAX_ROWS:
        raise ValueError("expected bounded record list")
    hits = []
    total_chars = 0
    for index,row in enumerate(records):
        if not isinstance(row,dict):
            raise ValueError("invalid record")
        role = _string(row.get("role",""),64)
        text = _string(row.get("text",""),8000)
        total_chars += len(text)+len(role)
        if total_chars > MAX_CHARS:
            raise ValueError("transcript exceeds input budget")
        if query in text.casefold():
            hits.append({"index":index,"role":role,"text":text})
    return {"matches":hits[:limit],"match_count":len(hits),"truncated":len(hits)>limit,
            "scope":"supplied_records_only"}


def search_registered_skills(orchestrator, query, limit=8):
    query = _string(query,512)
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    tokens = set(re.findall(r"[a-z0-9]+",query.casefold()))
    if not tokens:
        raise ValueError("query must contain search terms")
    hits = []
    for name,(description,handler) in orchestrator.tools.items():
        if not callable(handler):
            continue
        names = set(re.findall(r"[a-z0-9]+",name.casefold()))
        words = set(re.findall(r"[a-z0-9]+",description.casefold()))
        score = 3*len(names & tokens)+len(words & tokens)
        if score:
            hits.append({"name":name,"description":description,"score":score})
    hits.sort(key=lambda x:(-x["score"],x["name"]))
    return {"matches":hits[:limit],"match_count":len(hits),"scope":"registered_native_tools",
            "execution_verified":False}


def register_portable_skills(orchestrator):
    for name,description,handler in (
        ("profile_csv","Profile supplied CSV: {text:str}; returns row_count and per-column present, missing, distinct counts",profile_csv),
        ("group_csv_sum","Group supplied CSV and sum decimal column exactly: {text:str,group:str,value:str}; returns groups with sum as decimal text",group_csv_sum),
        ("search_transcript","Search explicitly supplied transcript: {records:[{role:str,text:str}],query:str,limit?:int}; returns exact matching observations with source indices",search_transcript),
    ):
        orchestrator.register(name,description,lambda args,task_ref,fn=handler: fn(**args))
    orchestrator.register("search_registered_skills",
        "Find available executable native skills by name and task vocabulary: {query:str,limit?:int}",
        lambda args,task_ref: search_registered_skills(orchestrator,**args))
