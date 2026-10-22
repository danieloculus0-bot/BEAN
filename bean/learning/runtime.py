"""Local BEAN Core Q-learning from host-observed outcomes.

Uses the original SpongeTD and SpongeIntuition. Not an LLM trainer,
truth verifier, or external-action engine.
"""
from __future__ import annotations

from bean.optimization.sponge_intuition import SpongeIntuition
from bean.optimization.sponge_td import SpongeTD

SCHEMA = "bean.learning.core.v1"


class LearningRuntime:
    def __init__(self, path, *, actions=("up", "right", "down", "left"), seed=0):
        self.policy = SpongeTD(path, actions=tuple(actions), seed=seed)
        self._episodes = {}

    @staticmethod
    def scoped(domain, state):
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError("nonempty task domain required")
        return ["bean-learning-v1", domain, state]

    def choose(self, *, episode_id, domain, state, location_ref,
               legal_actions, candidate_destinations=None):
        if not isinstance(episode_id, str) or not episode_id.strip():
            raise ValueError("nonempty episode_id required")
        if not isinstance(legal_actions, list) or not legal_actions:
            raise ValueError("legal_actions must be a nonempty list")
        if any(not isinstance(a, str) or a not in self.policy.actions
               for a in legal_actions) or len(set(legal_actions)) != len(legal_actions):
            raise ValueError("invalid, unknown or duplicate action")
        if candidate_destinations is not None and (
                not isinstance(candidate_destinations, dict) or
                any(a not in legal_actions for a in candidate_destinations)):
            raise ValueError("destinations must correspond to legal actions")
        observation = self.scoped(domain, state)
        location = self.scoped(domain, location_ref)
        self.policy.key(observation)
        self.policy.key(location)
        locations = {
            self.policy.actions.index(name): self.scoped(domain, destination)
            for name, destination in (candidate_destinations or {}).items()
        }
        for destination in locations.values():
            self.policy.key(destination)
        episode = self._episodes.get(episode_id)
        if episode is None:
            if len(self._episodes) >= 64:
                raise ValueError("too many active learning episodes")
            episode = {
                "domain": domain,
                "controller": SpongeIntuition(self.policy),
                "pending": None,
            }
            self._episodes[episode_id] = episode
        if episode["domain"] != domain:
            raise ValueError("episode domain mismatch")
        if episode["pending"] is not None:
            raise ValueError("feedback required before next choice")
        indices = [self.policy.actions.index(a) for a in legal_actions]
        action_index = episode["controller"].choose(
            observation, location_ref=location, legal_actions=indices,
            candidate_destinations=locations)
        episode["pending"] = (observation, action_index)
        return {
            "schema": SCHEMA, "episode_id": episode_id, "domain": domain,
            "action": self.policy.actions[action_index],
            "action_index": action_index,
            "decision": episode["controller"].last_decision,
            "q_updates": self.policy.steps,
            "learned_this_decision": False,
            "ground_truth_verified": False,
        }

    def feedback(self, *, episode_id, reward, next_state=None, done=False):
        episode = self._episodes.get(episode_id)
        if episode is None or episode["pending"] is None:
            raise ValueError("no uncredited choice for episode")
        if type(done) is not bool:
            raise ValueError("done must be boolean")
        if not done and next_state is None:
            raise ValueError("nonterminal feedback needs next_state")
        state, action_index = episode["pending"]
        following = None if done else self.scoped(episode["domain"], next_state)
        self.policy.learn(state, action_index, reward, following, done)
        episode["pending"] = None
        if done:
            del self._episodes[episode_id]
        return {
            "schema": SCHEMA, "learned": True, "episode_id": episode_id,
            "q_updates": self.policy.steps, "durable_checkpoint": False,
            "reward_origin": "host_reported_unverified",
        }

    def checkpoint(self, *, baseline, candidate, samples, evaluation_sha256):
        result = self.policy.checkpoint(
            baseline=baseline, candidate=candidate, samples=samples,
            evaluation_sha256=evaluation_sha256)
        return {"schema": SCHEMA, "checkpoint_saved": True, **result}

    def status(self):
        return {
            "schema": SCHEMA, "engine": "SpongeTD",
            "actions": list(self.policy.actions),
            "q_updates": self.policy.steps,
            "q_states": len(self.policy.q),
            "checkpoints": self.policy.checkpoints,
            "active_episodes": len(self._episodes),
            "pending_feedback": sum(
                x["pending"] is not None for x in self._episodes.values()),
            "storage": "local_sqlite_sha_journal",
            "model_training": False, "external_actions": False,
            "hosted_connector_integrated": False,
        }

    def close(self):
        self.policy.close()


def register_learning_handlers(inbox, service):
    """Plug the real Q engine into the existing BEAN command inbox."""
    inbox.register("learning_choose", lambda msg, _: service.choose(**msg.args))
    inbox.register("learning_feedback", lambda msg, _: service.feedback(**msg.args))
    inbox.register("learning_checkpoint", lambda msg, _: service.checkpoint(**msg.args))
    inbox.register("learning_status", lambda msg, _: service.status())
    return inbox
