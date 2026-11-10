"""Regression: invalid public reply wiring must not mutate persisted Core state."""
import tempfile
import unittest
from pathlib import Path
from scripts.invoke_bean import invoke


class PublicRequestPreflightTests(unittest.TestCase):
    def test_missing_reply_destination_rejected_before_runtime_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state"
            runtime = root / "runtime"
            with self.assertRaisesRegex(ValueError, "reply destination"):
                invoke(state, runtime, request={
                    "schema": "bean.github.request.v1",
                    "command": "reasoning_status",
                    "args": {},
                })
            self.assertFalse(state.exists())
            self.assertFalse(runtime.exists())

    def test_missing_reply_destination_preserves_existing_checkpoint_bytes(self):
        """Existing synthetic archives and runtime files must remain byte-identical."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state"
            runtime = root / "runtime"
            state.mkdir()
            runtime.mkdir()
            # Deliberately invalid placeholder archives: preflight must reject
            # before unpack attempts to parse them or touch the runtime.
            sentinels = {
                state / "manifest.json": b"synthetic-placeholder-manifest",
                state / "bean_memory.sqlite3.gz": b"synthetic-placeholder-core",
                state / "bean_reasoning.sqlite3.gz": b"synthetic-placeholder-reasoning",
                runtime / "existing.txt": b"existing-runtime-state",
            }
            for path, data in sentinels.items():
                path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "reply destination"):
                invoke(state, runtime, request={
                    "schema": "bean.github.request.v1",
                    "command": "reasoning_status",
                    "args": {},
                })
            self.assertEqual(
                {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()},
                {str(p.relative_to(root)): data for p, data in sentinels.items()},
            )


if __name__ == "__main__":
    unittest.main()
