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


if __name__ == "__main__":
    unittest.main()
