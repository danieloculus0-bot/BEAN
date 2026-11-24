"""Evidence-backed planner working memory, inspired by editable Letta memory
blocks and Mem0 selective consolidation. Original BEAN implementation;
raw observations remain in the canonical orchestration ledger.
"""
import hashlib
import json
import re

SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_working_memory_focus (
    session_uuid TEXT NOT NULL, proposal_id TEXT NOT NULL,
    PRIMARY KEY(session_uuid, proposal_id)
);
"""


def _tokens(value):
    return set(re.findall(r"[a-z0-9]{3,}", value.casefold()))


class WorkingMemory:
    def __init__(self, store, session):
        self.store, self.session = store, session
        store._conn().executescript(SCHEMA)
        store.commit()

    def _rows(self):
        return self.store.fetchall("""
            SELECT o.proposal_id,o.tool,o.output_json,o.output_sha256,p.action_detail,
                   CASE WHEN f.proposal_id IS NULL THEN 0 ELSE 1 END AS focused
            FROM bean_orchestration_outputs o
            JOIN cognition_goal_proposals p ON p.proposal_id=o.proposal_id
            LEFT JOIN bean_working_memory_focus f
              ON f.proposal_id=o.proposal_id AND f.session_uuid=p.session_uuid
            WHERE p.session_uuid=? AND o.tool NOT IN ('working_memory_search','working_memory_focus')
            ORDER BY focused DESC,o.rowid DESC LIMIT 512
        """, (self.session,))

    def search(self, query, limit=8):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("working memory query required")
        if type(limit) is not int or not 1 <= limit <= 12:
            raise ValueError("limit must be 1..12")
        wanted = _tokens(query[:2000])
        grouped = {}
        for row in self._rows():
            raw = row["output_json"]
            if hashlib.sha256(raw.encode("utf-8")).hexdigest() != row["output_sha256"]:
                continue
            try:
                out = json.loads(raw)
                detail = json.loads(row["action_detail"] or "{}")
            except (TypeError, ValueError):
                continue
            if not isinstance(detail, dict) or not isinstance(detail.get("objective", ""), str):
                continue
            objective = detail.get("objective", "")
            status = out.get("status") if isinstance(out, dict) else None
            key = (row["tool"], row["output_sha256"], objective)
            if key not in grouped:
                match = len(wanted & _tokens(objective + " " + row["tool"] + " " + raw[:3000]))
                if not match and not row["focused"]:
                    continue
                grouped[key] = {
                    "tool": row["tool"], "objective": objective[:500],
                    "output_sha256": row["output_sha256"], "status": status,
                    "passed": out.get("passed") if isinstance(out, dict) else None,
                    "observation_excerpt": raw[:600], "source_ids": [],
                    "focused": bool(row["focused"]), "relevance": match,
                    "independently_verified": False,
                }
            item = grouped[key]
            item["source_ids"].append(row["proposal_id"])
            item["focused"] = item["focused"] or bool(row["focused"])
        ranked = sorted(grouped.values(), key=lambda x: (x["focused"], x["relevance"]), reverse=True)
        return {"memories": ranked[:limit], "matching_groups": len(ranked),
                "scope": "current_session", "raw_history_preserved": True}

    def focus(self, source_ids):
        if not isinstance(source_ids, list) or len(source_ids) > 8 or any(
                not isinstance(x, str) for x in source_ids):
            raise ValueError("choose up to eight source IDs")
        valid = {row["proposal_id"] for row in self._rows()
                 if hashlib.sha256(row["output_json"].encode("utf-8")).hexdigest() == row["output_sha256"]}
        if not set(source_ids) <= valid:
            raise ValueError("source is unavailable in this session")
        with self.store._conn() as db:
            db.execute("DELETE FROM bean_working_memory_focus WHERE session_uuid=?", (self.session,))
            db.executemany("INSERT INTO bean_working_memory_focus VALUES (?,?)",
                           [(self.session, item) for item in sorted(set(source_ids))])
        return {"status": "success", "focused": len(set(source_ids)),
                "raw_history_preserved": True}
