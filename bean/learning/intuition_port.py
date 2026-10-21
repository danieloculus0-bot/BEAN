"""Optional bridge between BEAN Lab026 reasoning and native SpongeTD action intuition.

This joins *already journaled* strategy selection to *already trained* Q-values.
It does not train autonomously, expose external actions, or install a new policy.
"""
from __future__ import annotations

from hashlib import sha256
from bean.optimization.autodev import canonical
from bean.optimization.sponge_intuition import SpongeIntuition
from bean.optimization.sponge_td import SpongeTD, OBJECTIVE
from .native_skills import BEANReasoningSkills

SCHEMA = "bean.intuition.reasoned_action.v1"


class ReasonedIntuitionSession:
    """One task episode, tied to a measured BEAN lesson and Q checkpoint."""

    def __init__(self, *, skills, policy, domain, task_ref, query,
                 seed=0, visit_penalty=0.5, revisit_penalty=0.2,
                 lookback=10):
        if not isinstance(skills, BEANReasoningSkills):
            raise TypeError("BEAN native skill journal required")
        if not isinstance(policy, SpongeTD):
            raise TypeError("Original BEAN SpongeTD policy required")
        self.decision = skills.decide(domain=domain, task_ref=task_ref, query=query)
        self.policy = policy
        self.controller = SpongeIntuition(
            policy, seed=seed, visit_penalty=visit_penalty,
            revisit_penalty=revisit_penalty, lookback=lookback)
        self.policy_sha_at_start = sha256(canonical(policy.q)).hexdigest()
        history = policy.journal.events(OBJECTIVE)
        self.checkpoint = (history[-1]["quality"]["receipt_sha256"] if history else None)
        self.memory_receipt = (history[-1]["memory"]["sha256"] if history else None)
        if self.checkpoint is not None and self.memory_receipt is None:
            raise ValueError("Trained checkpoint lacks compressed memory source")

    def choose(self, state, *, location_ref, legal_actions,
               candidate_destinations=None):
        action = self.controller.choose(
            state, location_ref=location_ref, legal_actions=legal_actions,
            candidate_destinations=candidate_destinations)
        if sha256(canonical(self.policy.q)).hexdigest() != self.policy_sha_at_start:
            raise ValueError("Reasoned evaluation unexpectedly changed learned weights")
        return {
            "schema": SCHEMA,
            "task_ref": self.decision["task_ref"],
            "domain": self.decision["domain"],
            "chosen_action": self.policy.actions[action],
            "action_index": action,
            "action_reason": self.controller.last_decision,
            "reasoning_strategy": self.decision["selected_strategy"],
            "retrieved_lessons": self.decision["lessons"],
            "strategy_trial_hash": self.decision["selection_trial_hash"],
            "q_model_sha256": self.policy_sha_at_start,
            "q_checkpoint_evaluation_hash": self.checkpoint,
            "q_compressed_memory_sha256": self.memory_receipt,
            "policy_durable": self.memory_receipt is not None,
            "provider_called": False,
            "external_action_executed": False,
            "evidence_independently_authenticated": False,
        }
