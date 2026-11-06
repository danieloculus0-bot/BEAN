"""Regression tests for bounded canonical event retrieval (synthetic only)."""
import unittest
from unittest.mock import patch

from bean.memory.event_logger import EventType, get_events_by_type, get_recent_events


class EventHistoryBoundsTests(unittest.TestCase):
    def test_invalid_limits_never_query_store(self):
        for limit in (-1, 0, True, 1001, 1.5, "5", None):
            with self.subTest(limit=limit), patch("bean.memory.event_logger.get_store") as store:
                with self.assertRaises(ValueError):
                    get_recent_events("synthetic-session", limit)
                with self.assertRaises(ValueError):
                    get_events_by_type(EventType.OBSERVATION, limit)
                store.assert_not_called()

    def test_valid_limits_remain_sql_parameters(self):
        with patch("bean.memory.event_logger.get_store") as store:
            store.return_value.fetchall.return_value = []
            self.assertEqual(get_recent_events("synthetic-session", 1), [])
            self.assertEqual(store.return_value.fetchall.call_args.args[1], ("synthetic-session", 1))
            self.assertEqual(get_events_by_type(EventType.OBSERVATION, 1000), [])
            self.assertEqual(store.return_value.fetchall.call_args.args[1], ("observation", 1000))


if __name__ == "__main__":
    unittest.main()
