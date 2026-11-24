import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bean.runtime.working_memory import WorkingMemory


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS bean_orchestration_outputs (
                proposal_id TEXT PRIMARY KEY, tool TEXT, output_json TEXT, output_sha256 TEXT);
            CREATE TABLE IF NOT EXISTS cognition_goal_proposals (
                proposal_id TEXT PRIMARY KEY, session_uuid TEXT, action_detail TEXT);
        """)

    def _conn(self):
        return self.db

    def commit(self):
        self.db.commit()

    def fetchall(self, sql, params):
        return self.db.execute(sql, params).fetchall()

    def insert(self, id, session, objective, result, corrupt=False):
        raw = json.dumps(result, sort_keys=True)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        self.db.execute("INSERT INTO cognition_goal_proposals VALUES (?,?,?)",
                        (id, session, json.dumps({"objective": objective})))
        self.db.execute("INSERT INTO bean_orchestration_outputs VALUES (?,?,?,?)",
                        (id, "reason", raw, "invalid" if corrupt else digest))
        self.commit()


class WorkingMemoryTests(unittest.TestCase):
    def test_relevance_deduplication_scope_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.sqlite"
            store = Store(path)
            for id in ("a", "b"):
                store.insert(id, "session", "orbital velocity", {"status": "success", "speed": 7})
            store.insert("c", "session", "drawing bicycle", {"status": "failed"})
            store.insert("d", "other", "orbital velocity", {"status": "success", "speed": 9})
            store.insert("e", "session", "orbital velocity", {"status": "success"}, corrupt=True)
            memory = WorkingMemory(store, "session")
            result = memory.search("orbital velocity")
            self.assertEqual(result["matching_groups"], 1)
            self.assertEqual(set(result["memories"][0]["source_ids"]), {"a", "b"})
            with self.assertRaises(ValueError):
                memory.focus(["d"])
            with self.assertRaises(ValueError):
                memory.focus(["e"])
            memory.focus(["c"])
            store.db.close()
            store = Store(path)
            memory = WorkingMemory(store, "session")
            result = memory.search("orbital velocity")
            self.assertEqual(result["memories"][0]["source_ids"], ["c"])
            self.assertEqual(result["memories"][0]["status"], "failed")
            memory.focus([])
            self.assertEqual(memory.search("orbital velocity")["matching_groups"], 1)
            self.assertEqual(store.db.execute("SELECT count(*) FROM bean_orchestration_outputs").fetchone()[0], 5)
            store.db.close()


if __name__ == "__main__":
    unittest.main()
