"""Synthetic offline temporal-leakage controls for candidate precedent retrieval.

Research-only, not production Core or ExperienceBank integration.
Run: python -m unittest -v test_temporal_precedent_leakage.py
"""
import random
import unittest

STOP = {'the', 'and', 'with', 'from', 'task', 'procedure'}

def tokens(text):
    return set(text.lower().split()) - STOP

def retrieve(query, target_domain, query_time, lessons, *, temporal_guard):
    wanted = tokens(query)
    matches = []
    for lesson in lessons:
        if lesson['domain'] == target_domain:
            continue
        if temporal_guard and lesson['time'] >= query_time:
            continue
        overlap = len(wanted & tokens(lesson['text']))
        if overlap >= 2:
            matches.append((-overlap, lesson['id']))
    return [lesson_id for _, lesson_id in sorted(matches)]

class TemporalPrecedentLeakage(unittest.TestCase):
    def setUp(self):
        rng = random.Random(20261104)
        self.lessons = []
        self.cases = []
        for i in range(80):
            a, b = f'feature{i}', f'constraint{i}'
            query = f'{a} {b} repair'
            self.cases.append((query, f'target{i}', 100 + i, f'future{i}'))
            self.lessons.append(dict(id=f'past{i}', domain=f'source{i}', time=i,
                                     text=f'{a} {b} unrelated'))
            self.lessons.append(dict(id=f'future{i}', domain=f'source{i}', time=1000 + i,
                                     text=query))
        rng.shuffle(self.lessons)

    def test_future_records_are_retrieved_by_unprotected_baseline(self):
        contaminated = sum(future in retrieve(q, d, t, self.lessons, temporal_guard=False)
                           for q, d, t, future in self.cases)
        self.assertEqual(contaminated, 80)

    def test_temporal_guard_excludes_future_and_retains_past_candidates(self):
        for i, (q, d, t, future) in enumerate(self.cases):
            hits = retrieve(q, d, t, self.lessons, temporal_guard=True)
            self.assertNotIn(future, hits)
            self.assertIn(f'past{i}', hits)

    def test_equal_timestamp_is_not_historical_evidence(self):
        row = dict(id='same', domain='other', time=10, text='bolt torque repair')
        self.assertEqual(retrieve('bolt torque', 'target', 10, [row], temporal_guard=True), [])

    def test_restart_order_and_irrelevant_domain_invariant(self):
        q, d, t, _ = self.cases[0]
        first = retrieve(q, d, t, self.lessons, temporal_guard=True)
        replay = list(reversed(self.lessons))
        replay.append(dict(id='same-domain', domain=d, time=1, text=q))
        self.assertEqual(first, retrieve(q, d, t, replay, temporal_guard=True))

    def test_negative_control_guard_cannot_validate_transfer(self):
        q, d, t, _ = self.cases[0]
        self.assertTrue(retrieve(q, d, t, self.lessons, temporal_guard=True))
        self.assertEqual(sum(1 for row in self.lessons if row.get('target_verified')), 0)

if __name__ == '__main__':
    unittest.main()
