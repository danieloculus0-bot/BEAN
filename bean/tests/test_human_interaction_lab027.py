"""Lab027 adaptation regression tests; no model inference."""
import tempfile
import unittest
from pathlib import Path

from experiments.human_interaction.adaptive import AdaptiveInteraction, context_key


class AdaptiveInteractionTests(unittest.TestCase):
    def test_feedback_changes_action_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feedback.sqlite"
            before = "This manager can elave"
            turn = "leave"
            agent = AdaptiveInteraction(path)
            try:
                self.assertEqual(agent.act(before, turn)["action"], "exit")
                agent.learn(before, turn, "exit", -1)
                agent.learn(before, turn, "correction", 1)
                self.assertEqual(agent.act(before, turn)["action"], "correction")
                self.assertEqual(len(agent.journal()), 2)
            finally:
                agent.close()
            restarted = AdaptiveInteraction(path)
            try:
                self.assertEqual(restarted.act(before, turn)["action"], "correction")
                # Generalizes to a novel sentence exhibiting the same typo pattern.
                self.assertEqual(restarted.act("Go ahead and elave", "leave")["action"], "correction")
                # Does not assume every one-word message is a correction.
                self.assertEqual(restarted.act("Please go now", "leave")["action"], "exit")
            finally:
                restarted.close()

    def test_repeated_negative_feedback_can_revise_previous_lesson(self):
        with tempfile.TemporaryDirectory() as folder:
            agent = AdaptiveInteraction(Path(folder) / "db.sqlite")
            try:
                agent.learn("He can elave", "leave", "correction", 1)
                self.assertEqual(agent.choose("He can elave", "leave")["action"], "correction")
                for _ in range(6):
                    agent.learn("He can elave", "leave", "correction", -1)
                self.assertNotEqual(agent.choose("He can elave", "leave")["action"], "correction")
            finally:
                agent.close()

    def test_invalid_feedback_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            agent = AdaptiveInteraction(Path(folder) / "db.sqlite")
            try:
                with self.assertRaises(ValueError):
                    agent.learn("elave", "leave", "execute_shell", 1)
                with self.assertRaises(ValueError):
                    agent.learn("elave", "leave", "exit", 5)
                self.assertEqual(agent.journal(), [])
            finally:
                agent.close()

    def test_feature_key_omits_transcript(self):
        key = context_key("The project manager can elave", "leave")
        self.assertEqual(key, "single-word/preceding-transposition")
        self.assertNotIn("manager", key)


if __name__ == "__main__":
    unittest.main()
