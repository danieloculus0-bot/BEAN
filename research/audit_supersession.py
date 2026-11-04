"""Read-only audit of BEAN's existing SQLite event supersession graph.

Research diagnostic, not a replacement memory store or inference policy.
Usage: python research/audit_supersession.py /path/to/bean_memory.db
Self-test: python research/audit_supersession.py --self-test
"""
import argparse
import json
import sqlite3
import sys
import unittest
from pathlib import Path


def audit(connection):
    """Return deterministic findings without modifying event history."""
    rows = connection.execute(
        "SELECT id, superseded_by FROM events ORDER BY id"
    ).fetchall()
    links = {int(i): (None if nxt is None else int(nxt)) for i, nxt in rows}
    findings = []
    for origin, target in links.items():
        if target is None:
            continue
        if target not in links:
            findings.append({"kind": "missing_target", "event_id": origin, "target": target})
        elif target <= origin:
            findings.append({"kind": "non_forward_link", "event_id": origin, "target": target})
    # An increasing-ID chain cannot cycle. Still detect cycles independently,
    # because legacy or externally written databases may contain bad links.
    seen_global = set()
    for origin in links:
        if origin in seen_global:
            continue
        path = []
        positions = {}
        current = origin
        while current is not None and current in links and current not in seen_global:
            if current in positions:
                cycle = path[positions[current]:]
                findings.append({"kind": "cycle", "event_ids": sorted(cycle)})
                break
            positions[current] = len(path)
            path.append(current)
            current = links[current]
        seen_global.update(path)
    return {"event_count": len(links), "supersession_count": sum(x is not None for x in links.values()),
            "findings": sorted(findings, key=lambda x: (x["kind"], x.get("event_id", -1), x.get("event_ids", [])))}


class SyntheticAuditTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE events(id INTEGER PRIMARY KEY, superseded_by INTEGER)")

    def tearDown(self):
        self.db.close()

    def seed(self, pairs):
        self.db.executemany("INSERT INTO events VALUES (?, ?)", pairs)
        return audit(self.db)

    def test_valid_forward_chain(self):
        result = self.seed([(1, 2), (2, 3), (3, None)])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["supersession_count"], 2)

    def test_missing_target(self):
        self.assertEqual(self.seed([(1, 99)])["findings"][0]["kind"], "missing_target")

    def test_self_reference(self):
        kinds = {f["kind"] for f in self.seed([(1, 1)])["findings"]}
        self.assertEqual(kinds, {"cycle", "non_forward_link"})

    def test_two_event_cycle(self):
        result = self.seed([(1, 2), (2, 1)])
        self.assertEqual([f["kind"] for f in result["findings"]], ["cycle", "non_forward_link"])

    def test_backward_without_cycle(self):
        result = self.seed([(1, None), (2, 1)])
        self.assertEqual([f["kind"] for f in result["findings"]], ["non_forward_link"])

    def test_read_only(self):
        self.seed([(1, 2), (2, None)])
        before = self.db.total_changes
        audit(self.db)
        self.assertEqual(self.db.total_changes, before)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticAuditTests)
        sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if not args.database:
        parser.error("database required unless --self-test is supplied")
    uri = f"file:{Path(args.database).resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        result = audit(conn)
    print(json.dumps(result, sort_keys=True, indent=2))
    sys.exit(bool(result["findings"]))
