"""BEAN's retained memory append must not rescan and reverify the history twice."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bean.learning.experimental import ExperienceBank, Lesson


class JournalAppendEfficiencyTests(unittest.TestCase):
    def test_append_reuses_journal_own_integrity_check_without_duplicate_replay(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"history.sqlite3"
            bank=ExperienceBank(path)
            try:
                for index in range(12):
                    l=Lesson("lesson-%03d" % index, "prompt", "sample",
                             "remember observed-%d" % index,
                             ("evidence:sample-%d" % index,),
                             "host_reported")
                    with patch.object(bank.journal, "events",
                                      wraps=bank.journal.events) as calls:
                        bank.add(l)
                    # add() checks for duplicates once; _append() no longer
                    # redundantly reads and verifies history before Journal.append.
                    self.assertEqual(calls.call_count, 1)
                rows=bank.journal.events()
                self.assertEqual([r["iteration"] for r in rows], list(range(1,13)))
            finally:
                bank.close()
            recovered=ExperienceBank(path)
            try:
                self.assertEqual(len(recovered.lessons()), 12)
                self.assertEqual(len(recovered.journal.events()), 12)
            finally:
                recovered.close()


if __name__ == "__main__":
    unittest.main()
