"""Ledger integrity and explicit separation of data-window experiments."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from .ledger import append_result, verify


def fixture(key):
    return {
        "run_key": key,
        "protocol": {"train_offset": 900000 if key == "first" else 1200000},
        "selected_episode": 1000,
        "checkpoints": [{"episode": 0,
                         "validation": {"bricks": 1.0},
                         "receipt": {"memory_sha256": "a" * 64}}],
        "holdout": {"cold": {"bricks": 1.0}, "selected": {"bricks": 3.0}},
        "holdout_delta": 2.0,
        "journal_tip": "f" * 64,
        "source_digests": {"game_py": "b" * 64, "sponge_td_py": "c" * 64},
    }


class LedgerTests(unittest.TestCase):
    def test_append_restart_and_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "receipts.jsonl"
            first = append_result(ledger, fixture("first"))
            second = append_result(ledger, fixture("second"))
            rows = verify(ledger)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["previous_sha256"], first["entry_sha256"])
            self.assertEqual(rows[-1]["entry_sha256"], second["entry_sha256"])
            with self.assertRaisesRegex(ValueError, "already recorded"):
                append_result(ledger, fixture("first"))

    def test_tampered_score_and_deleted_row_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "receipts.jsonl"
            append_result(ledger, fixture("first"))
            append_result(ledger, fixture("second"))
            lines = ledger.read_text().splitlines()
            tampered = json.loads(lines[0])
            tampered["holdout_delta"] = 999
            ledger.write_text(json.dumps(tampered) + "\n" + lines[1] + "\n")
            with self.assertRaisesRegex(ValueError, "chain broken"):
                verify(ledger)
            ledger.write_text(lines[1] + "\n")
            with self.assertRaisesRegex(ValueError, "chain broken"):
                verify(ledger)

    def test_persist_unchanged_and_reject_conflicting_replays(self):
        from .publish_ledger import merge
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            temporary = folder / "ci.jsonl"
            persistent = folder / "research.jsonl"
            append_result(temporary, fixture("first"))
            self.assertEqual(merge(temporary, persistent), 1)
            self.assertEqual(merge(temporary, persistent), 0)
            append_result(temporary, fixture("second"))
            self.assertEqual(merge(temporary, persistent), 1)
            self.assertEqual(len(verify(persistent)), 2)
            incompatible = fixture("first")
            incompatible["holdout_delta"] = 9
            competing = folder / "conflict.jsonl"
            append_result(competing, incompatible)
            with self.assertRaisesRegex(ValueError, "conflicting historical run"):
                merge(competing, persistent)

    def test_source_hash_ignores_windows_checkout_newlines(self):
        from .train import digest_source
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.py"
            path.write_bytes(b"print('hello')\\nprint('world')\\n".replace(b"\\n", b"\n"))
            first = digest_source(path)
            path.write_bytes(b"print('hello')\\r\\nprint('world')\\r\\n".replace(b"\\r\\n", b"\r\n"))
            self.assertEqual(first, digest_source(path))

    def test_seed_overlap_rejected_without_running_training(self):
        from .train import run
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "disjoint"):
                run(Path(tmp) / "test", train_offset=1000,
                    validation_offset=1100, holdout_offset=5000)


if __name__ == "__main__":
    unittest.main()
