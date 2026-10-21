"""Experimental cross-application state memory and Q-learning ledger.

Persistent truth is the append-only, hash-linked, zlib-compressed event stream.
The small, queryable Q-table is a derived cache, never a substitute for receipts.
This isolated research store does not replace BEAN Core's canonical event logger.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import zlib

SCHEMA = "bean.portfolio.ledger.v1"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identifier(value, name):
    if not isinstance(value, str) or not value or len(value) > 160:
        raise ValueError(f"invalid {name}")
    return value


class PortfolioLedger:
    """One local store for many apps; outcomes train only their app's policy.

    Consumers supply independently measured outcomes or clearly marked synthetic
    outcomes. Nothing connects to real shop systems or trading engines by itself.
    """

    def __init__(self, path):
        p = Path(path)
        if str(path) != ":memory:":
            p.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio_events (
          seq INTEGER PRIMARY KEY AUTOINCREMENT,
          app TEXT NOT NULL, event_id TEXT NOT NULL, kind TEXT NOT NULL,
          compressed BLOB NOT NULL, payload_hash TEXT NOT NULL,
          previous_hash TEXT NOT NULL, chain_hash TEXT NOT NULL,
          inserted_at TEXT NOT NULL, UNIQUE(app,event_id)
        );
        CREATE TABLE IF NOT EXISTS portfolio_q (
          app TEXT NOT NULL, state TEXT NOT NULL, action TEXT NOT NULL,
          value REAL NOT NULL, updates INTEGER NOT NULL,
          PRIMARY KEY (app,state,action)
        );
        CREATE TABLE IF NOT EXISTS portfolio_scores (
          app TEXT PRIMARY KEY, rewarded INTEGER NOT NULL,
          positive INTEGER NOT NULL, negative INTEGER NOT NULL,
          zero INTEGER NOT NULL, reward_sum REAL NOT NULL
        );
        """)
        self.db.commit()

    def _q(self, app, state):
        return {r["action"]: r["value"] for r in self.db.execute(
            "SELECT action,value FROM portfolio_q WHERE app=? AND state=?",
            (app, state))}

    def observe(self, *, app, event_id, state, action=None, reward=None,
                next_state=None, done=False, evidence_ref, kind="measured",
                alpha=0.23, gamma=0.975, tags=(), revision="unspecified"):
        """Append once and apply at most one TD update, atomically.

        reward=None means observation only. No guesswork or auto-reward.
        Same event_id and payload is a no-op; different payload is a conflict.
        """
        app = identifier(app, "app")
        event_id = identifier(event_id, "event_id")
        state = identifier(state, "state")
        evidence_ref = identifier(evidence_ref, "evidence_ref")
        revision = identifier(revision, "revision")
        if kind not in ("measured", "synthetic", "unverified"):
            raise ValueError("unknown evidence class")
        if type(done) is not bool or not (0 < alpha <= 1 and 0 <= gamma <= 1):
            raise ValueError("invalid Q configuration")
        if not isinstance(tags, (tuple, list)) or len(tags) > 8 or not all(
                isinstance(tag, str) and 0 < len(tag) <= 50 for tag in tags):
            raise ValueError("invalid tags")
        if reward is not None:
            if kind == "unverified":
                raise ValueError("unverified observations cannot earn Q reward")
            if not (type(reward) in (int, float) and math.isfinite(reward) and abs(reward)<=1e6):
                raise ValueError("invalid reward")
            if not isinstance(action, str) or not action or len(action) > 80:
                raise ValueError("reward needs an action")
            if not done:
                next_state = identifier(next_state, "next_state")
        elif action is not None and not isinstance(action, str):
            raise ValueError("invalid action")
        doc = {"schema": SCHEMA, "app": app, "event_id": event_id,
               "state": state, "action": action, "reward": reward,
               "next_state": next_state, "done": done,
               "evidence_ref": evidence_ref, "kind": kind,
               "tags": list(tags), "revision": revision,
               "alpha": alpha, "gamma": gamma}
        data = canonical(doc)
        if len(data) > 16384:
            raise ValueError("event too large")
        fingerprint = sha(data)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.db.execute(
                "SELECT payload_hash,chain_hash FROM portfolio_events "
                "WHERE app=? AND event_id=?", (app, event_id)).fetchone()
            if old:
                if old["payload_hash"] != fingerprint:
                    raise ValueError("conflicting evidence event identity")
                return {"new": False, "receipt": old["chain_hash"]}
            prior = self.db.execute(
                "SELECT chain_hash FROM portfolio_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            previous = prior[0] if prior else "GENESIS"
            tip = sha(canonical([previous, fingerprint]))
            self.db.execute("""
                INSERT INTO portfolio_events
                (app,event_id,kind,compressed,payload_hash,previous_hash,
                 chain_hash,inserted_at) VALUES(?,?,?,?,?,?,?,?)""",
                (app,event_id,kind,zlib.compress(data,9),fingerprint,previous,
                 tip,datetime.now(timezone.utc).isoformat()))
            if reward is not None:
                current = self._q(app, state).get(action, 0.0)
                future = max(self._q(app, next_state).values(), default=0.0) if not done else 0
                updated = current + alpha * (reward + gamma * future - current)
                if not math.isfinite(updated):
                    raise ValueError("Q update overflow")
                self.db.execute("""
                    INSERT INTO portfolio_q(app,state,action,value,updates)
                    VALUES (?,?,?,?,1)
                    ON CONFLICT(app,state,action) DO UPDATE SET
                    value=excluded.value,updates=portfolio_q.updates+1
                    """, (app,state,action,updated))
                self.db.execute("""
                    INSERT INTO portfolio_scores
                    (app,rewarded,positive,negative,zero,reward_sum)
                    VALUES (?,?,?,?,?,?)
                    ON CONFLICT(app) DO UPDATE SET
                    rewarded=portfolio_scores.rewarded+1,
                    positive=portfolio_scores.positive+excluded.positive,
                    negative=portfolio_scores.negative+excluded.negative,
                    zero=portfolio_scores.zero+excluded.zero,
                    reward_sum=portfolio_scores.reward_sum+excluded.reward_sum
                    """,(app,1,int(reward>0),int(reward<0),int(reward==0),
                         float(reward)))
        return {"new": True, "receipt": tip}

    def event(self, app, event_id):
        row = self.db.execute("SELECT * FROM portfolio_events WHERE app=? AND event_id=?",
                              (app,event_id)).fetchone()
        if row is None:
            return None
        raw = zlib.decompress(row["compressed"])
        if sha(raw) != row["payload_hash"]:
            raise ValueError("corrupt event payload")
        return json.loads(raw)

    def verify(self):
        """Verify entire archive and independently reconstruct the Q-table."""
        previous = "GENESIS"
        rebuilt = {}
        score_replay = {}
        rows = self.db.execute("SELECT * FROM portfolio_events ORDER BY seq")
        count = 0
        for row in rows:
            raw = zlib.decompress(row["compressed"])
            digest = sha(raw)
            expected = sha(canonical([previous, digest]))
            if (digest != row["payload_hash"] or row["previous_hash"] != previous
                    or row["chain_hash"] != expected):
                raise ValueError(f"event chain corrupted at row {row['seq']}")
            doc = json.loads(raw)
            if (doc.get("schema") != SCHEMA or doc["app"] != row["app"]
                    or doc["event_id"] != row["event_id"]):
                raise ValueError("event fields corrupted")
            if doc["reward"] is not None:
                tally=score_replay.setdefault(doc["app"],[0,0,0,0,0.0])
                tally[0]+=1
                tally[1]+=int(doc["reward"]>0)
                tally[2]+=int(doc["reward"]<0)
                tally[3]+=int(doc["reward"]==0)
                tally[4]+=float(doc["reward"])
                key = (doc["app"],doc["state"],doc["action"])
                old, updates = rebuilt.get(key, (0.0,0))
                possible = [value for (app,state,_), (value,_) in rebuilt.items()
                            if app == doc["app"] and state == doc["next_state"]]
                future = max(possible,default=0) if not doc["done"] else 0
                value = old + doc["alpha"] * (
                    doc["reward"] + doc["gamma"] * future - old)
                rebuilt[key] = (value,updates+1)
            previous, count = expected, count+1
        saved = {(r["app"],r["state"],r["action"]):(r["value"],r["updates"])
                 for r in self.db.execute("SELECT * FROM portfolio_q")}
        if rebuilt.keys() != saved.keys() or any(
            n != saved[k][1] or not math.isclose(v,saved[k][0],abs_tol=1e-10)
            for k,(v,n) in rebuilt.items()):
            raise ValueError("derived Q state diverges from ledger")
        scored = {r["app"]:(r["rewarded"],r["positive"],r["negative"],
                 r["zero"],r["reward_sum"])
                  for r in self.db.execute("SELECT * FROM portfolio_scores")}
        if scored.keys()!=score_replay.keys() or any(
            tuple(v[:4])!=scored[k][:4] or not math.isclose(v[4],scored[k][4],abs_tol=1e-7)
            for k,v in score_replay.items()):
            raise ValueError("derived reward scoreboard diverges from ledger")
        return {"events": count, "tip": previous, "q_entries": len(saved),
                "rewarded_events":sum(v[0] for v in score_replay.values())}

    def state_context(self, *, app, query="", max_bytes=2048, limit=12):
        """Return a bounded, task-relevant context instead of the entire log.

        Full receipts remain individually recoverable with event(app, event_id).
        A matching state/action is contextual information, not a proven benefit.
        """
        app = identifier(app, "app")
        if not isinstance(query,str) or len(query)>160:
            raise ValueError("invalid query")
        if not isinstance(max_bytes,int) or max_bytes < 400 or max_bytes>65536:
            raise ValueError("invalid context budget")
        if not isinstance(limit,int) or not 1<=limit<=100:
            raise ValueError("invalid limit")
        words = set(query.lower().replace("/"," ").replace("_"," ").split())
        candidates = []
        for row in self.db.execute(
            "SELECT event_id,kind,compressed,chain_hash,seq FROM portfolio_events "
            "WHERE app=? ORDER BY seq DESC LIMIT 400", (app,)):
            doc = json.loads(zlib.decompress(row["compressed"]))
            searchable = " ".join([doc["state"],doc["evidence_ref"],*doc["tags"]]).lower()
            match = sum(w in searchable for w in words)
            candidates.append((match,row["seq"],
                {"id":row["event_id"],"state":doc["state"],"action":doc["action"],
                 "reward":doc["reward"],"evidence":doc["evidence_ref"],
                 "receipt":row["chain_hash"][:16],"kind":doc["kind"]}))
        candidates.sort(key=lambda entry: (entry[0], entry[1]),reverse=True)
        learned = [{"state":r["state"],"action":r["action"],
                    "q":round(r["value"],6),"updates":r["updates"]}
                   for r in self.db.execute(
                       "SELECT state,action,value,updates FROM portfolio_q "
                       "WHERE app=? ORDER BY updates DESC LIMIT 100",(app,))]
        if words:
            learned.sort(key=lambda r:(-sum(w in r["state"].lower() for w in words),
                                       -r["updates"]))
        meta = self.db.execute(
            "SELECT COUNT(*) AS n,MAX(seq) AS newest FROM portfolio_events WHERE app=?",
            (app,)).fetchone()
        scored = self.db.execute(
            "SELECT rewarded,positive,negative,zero,reward_sum "
            "FROM portfolio_scores WHERE app=?",(app,)).fetchone()
        output = {"schema":SCHEMA,"app":app,"query":query,
                  "total_events":meta["n"],"newest_seq":meta["newest"],
                  "rewards":dict(scored) if scored else None,
                  "policy":[],"receipts":[],"truncated":False}
        def fits():
            return len(canonical(output)) <= max_bytes
        if not fits():
            raise ValueError("context metadata exceeds budget")
        for entry in learned[:limit]:
            output["policy"].append(entry)
            if not fits():
                output["policy"].pop()
                output["truncated"]=True
                break
        for _,__,entry in candidates[:limit]:
            output["receipts"].append(entry)
            if not fits():
                output["receipts"].pop()
                output["truncated"]=True
                break
        output["truncated"] |= len(candidates)>len(output["receipts"]) or len(learned)>len(output["policy"])
        while not fits():
            if output["receipts"]:
                output["receipts"].pop()
            elif output["policy"]:
                output["policy"].pop()
            else:
                raise ValueError("context budget too small")
        return output

    def portfolio_context(self, *, max_bytes=4096):
        """Small cross-repository scoreboard. Q policies remain app-isolated."""
        if not isinstance(max_bytes,int) or not 512<=max_bytes<=65536:
            raise ValueError("invalid portfolio context budget")
        rows = self.db.execute("""
            SELECT app,COUNT(*) AS events,MAX(seq) AS last_seq
            FROM portfolio_events GROUP BY app ORDER BY last_seq DESC
        """).fetchall()
        output = {"schema":SCHEMA,"scope":"all_apps",
                  "apps_total":len(rows),"apps":[],"apps_omitted":0}
        for row in rows:
            q = self.db.execute("""
                SELECT COUNT(*) AS states,COALESCE(SUM(updates),0) AS updates
                FROM portfolio_q WHERE app=?""",(row["app"],)).fetchone()
            latest = self.db.execute("""
                SELECT event_id,chain_hash FROM portfolio_events
                WHERE app=? ORDER BY seq DESC LIMIT 1""",(row["app"],)).fetchone()
            scores = self.db.execute(
                "SELECT rewarded,positive,negative,zero,reward_sum "
                "FROM portfolio_scores WHERE app=?",(row["app"],)).fetchone()
            summary = {"app":row["app"],"events":row["events"],
                       "q_entries":q["states"],"q_updates":q["updates"],
                       "rewards":dict(scores) if scores else None,
                       "latest_event":latest["event_id"],
                       "tip":latest["chain_hash"][:16]}
            output["apps"].append(summary)
            output["apps_omitted"]=len(rows)-len(output["apps"])
            if len(canonical(output))>max_bytes:
                output["apps"].pop()
                output["apps_omitted"]=len(rows)-len(output["apps"])
                break
        if len(canonical(output))>max_bytes:
            raise ValueError("portfolio context too small")
        return output

    def close(self):
        self.db.close()
