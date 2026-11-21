"""Synthetic independent-action learning using BEAN's native reasoning service.

Public, generic training fixture: no confidential hardware dimensions. A
physics solver measures each of the three actions. Only the sensors are
visible during policy induction; withheld validation probes are disjoint.
"""
import tempfile
import unittest
from pathlib import Path

from bean.engineering.rigid_body import solve_rigid_body_balance
from bean.learning.active_hypothesis import act, discover
from bean.learning.reasoning_service import NativeReasoningService


def observe(probe):
    kind, raw = probe.split('-', 1)
    i = int(raw) + (100 if kind == 'v' else 200 if kind == 'h' else 0)
    pivot_y = ((i * 7) % 11 - 5) * .003
    delta = (-.030, 0, .030)[i % 3]
    com_y = pivot_y + delta
    nuisance = ((i * 13) % 29 - 14) * .002 + i*.00001
    return (com_y, pivot_y, nuisance)


def measured_reward(probe, action):
    com_y, pivot_y, _ = observe(probe)
    run = solve_rigid_body_balance({
        'parts': [{'mass_kg': 1.0, 'center_m': [0, com_y]}],
        'pivot_m': [0, pivot_y + action*.012],
        'fill_fractions': [0],
        'spin_rps': 0,
    })
    return -100 * run['states'][0]['peak_gravity_torque_nm']


class RigidBodyAdaptiveTraining(unittest.TestCase):
    def test_native_learning_from_three_physics_actions_and_unseen_cases(self):
        train = [f't-{i}' for i in range(48)]
        validation = [f'v-{i}' for i in range(9)]
        with tempfile.TemporaryDirectory() as d:
            service = NativeReasoningService(Path(d) / 'experience.sqlite3')
            try:
                result = service.discover_analogy(
                    domain='rigid_body_pivot', task_ref='generic_fill_balance_training',
                    source_ref='bean/engineering/rigid_body.py',
                    probe_ids=train, validation_probe_ids=validation,
                    observe=observe, reward=measured_reward, budget=12,
                    method='disagreement', seed=18,
                )
                self.assertTrue(result['evidence_retained'])
                self.assertFalse(result['external_model_invoked'])
                self.assertEqual(result['status'], 'provisional_rule')
                self.assertIsNotNone(result['selected_rule'])
                self.assertTrue(result['validation']['passed'])
                self.assertEqual(result['reward_calls'], 63)
                self.assertFalse(result['blind_cases_used'])
                rule = result['selected_rule']
                holdout = [f'h-{i}' for i in range(24)]
                count = 0
                for pid in holdout:
                    predicted = act(rule, observe(pid))
                    actual = max((-1,0,1), key=lambda a: measured_reward(pid,a))
                    count += predicted == actual
                self.assertEqual(count, len(holdout))
            finally:
                service.close()

    def test_flat_rewards_trigger_abstention(self):
        outcome = discover(
            probe_ids=[f't-{i}' for i in range(12)], observe=observe,
            reward=lambda pid, action: 0.0, budget=8)
        self.assertEqual(outcome['status'], 'abstain')
        self.assertIsNone(outcome['selected_rule'])


if __name__=='__main__':unittest.main()
