"""Neutral synthetic repair challenges, unseen tests excluded from both prompts.

BEAN and Aider receive EXACTLY the same source and functional requirements.
The evaluator gets the independent test snippets only after both author jobs.
No tests are passed to either model. These are not claims about real ERP data.
"""
from __future__ import annotations
import hashlib
import json

CASES = {
  "ledger_revisions": {
    "prompt": (
      "Repair the single Python module candidate.py. Function replay(events, as_of) "
      "must return balances per account, from accepted signed integer deltas. "
      "Each input event has id, revision (nonnegative integer), account, delta "
      "(signed integer), and at (ISO-8601 with optional Z and explicit UTC offset). "
      "Ignore events occurring strictly after as_of (compare absolute instants). "
      "For repeated ids apply ONLY the eligible event with the highest revision; "
      "repeat copies of the same revision must not double count. Events with "
      "different ids can target the same account. Input event order never "
      "changes the result. No mutation of caller data, no additional packages. "
      "Preserve replay(events, as_of) as the public interface. Make the fix "
      "directly in candidate.py. The evaluator uses withheld tests."
    ),
    "source": '''from datetime import datetime


def parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def replay(events, as_of):
    """Compute as-of account balances from an event stream."""
    cutoff = parse(as_of)
    totals = {}
    for event in events:
        if parse(event["at"]) > cutoff:
            continue
        key = event["account"]
        totals[key] = totals.get(key, 0) + event["delta"]
    return totals
''',
    "test": '''import unittest
from candidate import replay


class TestRevisions(unittest.TestCase):
    def e(self, id, rev, acct, delta, at="2026-10-10T00:15:00Z"):
        return {"id": id, "revision": rev, "account": acct, "delta": delta, "at": at}

    def test_revisions_replace_previous_effect(self):
        events = [self.e("A", 1, "cash", 100), self.e("A", 2, "cash", 3)]
        self.assertEqual(replay(events, "2026-10-10T01:00:00Z"), {"cash": 3})

    def test_identical_duplicate_is_applied_once(self):
        e = self.e("T", 1, "cash", -7)
        self.assertEqual(replay([e, e, e], "2026-10-10T01:00:00Z"), {"cash": -7})

    def test_eligible_revision_even_if_future_revision_exists(self):
        rows = [self.e("A", 5, "cash", 50, "2026-10-11T03:00:00Z"),
                self.e("A", 4, "cash", 40)]
        self.assertEqual(replay(rows, "2026-10-10T01:00:00Z"), {"cash": 40})

    def test_latest_revision_not_latest_array_order(self):
        rows = [self.e("A", 5, "cash", 8), self.e("A", 1, "cash", 9)]
        self.assertEqual(replay(rows, "2026-10-10T01:00:00Z"),
                         replay(list(reversed(rows)), "2026-10-10T01:00:00Z"))
        self.assertEqual(replay(rows, "2026-10-10T01:00:00Z"), {"cash": 8})

    def test_timezone_instant_and_boundary(self):
        rows = [self.e("A", 1, "cash", 11, "2026-10-10T00:30:00+00:00"),
                self.e("B", 1, "cash", 9, "2026-10-10T00:31:00+00:00")]
        self.assertEqual(replay(rows, "2026-10-09T19:30:00-05:00"), {"cash": 11})

    def test_cross_account_revisions_follow_id(self):
        rows = [self.e("A", 1, "old", 5), self.e("A", 2, "new", 10),
                self.e("B", 1, "new", -2)]
        self.assertEqual(replay(rows, "2026-10-10T01:00:00Z"), {"new": 8})

    def test_empty(self):
        self.assertEqual(replay([], "2026-10-10T01:00:00Z"), {})

    def test_source_is_unchanged(self):
        rows = [self.e("A", 1, "cash", 1)]
        snapshot = [dict(r) for r in rows]
        replay(rows, "2026-10-10T01:00:00Z")
        self.assertEqual(rows, snapshot)


if __name__ == "__main__":
    unittest.main()
''',
  },
  "permission_graph": {
    "prompt": (
      "Repair the single Python module candidate.py. Function can_access(user, "
      "action, memberships, grants, denies) decides whether user has permission "
      "for action. memberships maps users or groups to lists of parent groups, "
      "and inheritance is TRANSITIVE. grants and denies each map principals "
      "(user/group) to allowed or forbidden action-name lists. An explicit "
      "deny ANYWHERE in the reachable user/group graph overrides EVERY grant, "
      "including direct grants. A grant anywhere reachable permits access "
      "if no reachable deny exists. Missing permission means False; nested "
      "groups can contain cycles and redundant membership edges, and results "
      "must be order-independent. No additional packages, no caller mutation, "
      "preserve the public can_access signature, modify candidate.py only. "
      "The evaluator uses withheld tests."
    ),
    "source": '''def can_access(user, action, memberships, grants, denies):
    """Return whether a principal is allowed to perform an action."""
    if action in grants.get(user, ()):
        return True
    for group in memberships.get(user, ()):
        if action in grants.get(group, ()):
            return True
    return False
''',
    "test": '''import unittest
from candidate import can_access


class TestPolicy(unittest.TestCase):
    def test_direct_grant(self):
        self.assertTrue(can_access("u", "read", {}, {"u": ["read"]}, {}))

    def test_unknown_denied(self):
        self.assertFalse(can_access("u", "write", {}, {}, {}))

    def test_two_level_grant(self):
        links = {"u": ["team"], "team": ["company"]}
        self.assertTrue(can_access("u", "read", links, {"company": ["read"]}, {}))

    def test_direct_deny_beats_inherited_allow(self):
        links = {"u": ["team"]}
        self.assertFalse(can_access("u", "read", links, {"team": ["read"]},
                                    {"u": ["read"]}))

    def test_transitive_deny_beats_direct_grant(self):
        links = {"u": ["team"], "team": ["restricted"]}
        self.assertFalse(can_access("u", "edit", links, {"u": ["edit"]},
                                    {"restricted": ["edit"]}))

    def test_deny_in_other_branch_overrides_allow(self):
        links = {"u": ["team_a", "team_b"]}
        self.assertFalse(can_access("u", "read", links, {"team_a": ["read"]},
                                    {"team_b": ["read"]}))

    def test_cycles_are_bounded(self):
        links = {"u": ["a"], "a": ["b"], "b": ["a"]}
        self.assertTrue(can_access("u", "read", links, {"b": ["read"]}, {}))
        self.assertFalse(can_access("u", "read", links, {"b": ["read"]},
                                    {"a": ["read"]}))

    def test_graph_permutation_and_caller_integrity(self):
        graph = {"u": ["first", "second"], "first": ["org"], "second": ["org"]}
        snap = {k:list(v) for k,v in graph.items()}
        grants = {"first": ["read"], "org": ["write"]}
        denies = {"second": ["read"]}
        self.assertFalse(can_access("u", "read", graph, grants, denies))
        graph["u"].reverse()
        self.assertFalse(can_access("u", "read", graph, grants, denies))
        graph["u"].reverse()
        self.assertEqual(graph, snap)


if __name__ == "__main__":
    unittest.main()
''',
  },
}

def public_case(name):
    row = CASES[name]
    return {"name": name, "prompt": row["prompt"], "source": row["source"],
            "source_sha256": hashlib.sha256(row["source"].encode()).hexdigest()}

def sealed_oracle_digest(name):
    return hashlib.sha256(CASES[name]["test"].encode()).hexdigest()

def manifest():
    return {
        "schema": "bean.vs.aider.arena.v1",
        "case_ids": list(CASES),
        "case_public_sha256": {
            name: hashlib.sha256(json.dumps(public_case(name), sort_keys=True).encode()).hexdigest()
            for name in CASES},
        "oracle_sha256": {name: sealed_oracle_digest(name) for name in CASES},
    }
