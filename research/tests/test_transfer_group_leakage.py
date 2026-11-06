"""Synthetic negative control: repeated-group leakage in transfer evaluation.

No BEAN Core integration or inference claim. Fixed seed/budget; labels are
independent of group ID, but group-specific latent bits are reusable within a
group. A memorizer can exploit that repetition if train/test share groups.
"""
import hashlib
import json
import random
import unittest


def evaluate(seed, *, groups=120, repeats=6, train_fraction=0.7):
    if groups < 10 or repeats < 2 or not 0 < train_fraction < 1:
        raise ValueError('invalid evaluation design')
    rng = random.Random(seed)
    group_ids = list(range(groups))
    rng.shuffle(group_ids)
    hidden = {g: rng.randrange(2) for g in group_ids}
    # Each group is assigned an unobserved random bit. Features are just a
    # group token; a new group offers no predictive signal about its label.
    rows = [(g, hidden[g]) for g in group_ids for _ in range(repeats)]
    rng.shuffle(rows)
    cutoff = int(len(rows) * train_fraction)
    row_train, row_test = rows[:cutoff], rows[cutoff:]
    split = int(groups * train_fraction)
    held_groups = set(group_ids[split:])
    group_train = [r for r in rows if r[0] not in held_groups]
    group_test = [r for r in rows if r[0] in held_groups]

    def score(train, test):
        memory = {g: y for g, y in train}
        correct = sum(memory.get(g, 0) == y for g, y in test)
        return {'accuracy': correct / len(test), 'seen_fraction':
                sum(g in memory for g, _ in test) / len(test), 'n': len(test)}

    result = {'seed': seed, 'groups': groups, 'repeats': repeats,
              'row_split': score(row_train, row_test),
              'group_split': score(group_train, group_test),
              'baseline': {'constant_zero_group_accuracy':
                           sum(y == 0 for _, y in group_test) / len(group_test)}}
    payload = json.dumps(result, sort_keys=True, separators=(',', ':'))
    return result, hashlib.sha256(payload.encode()).hexdigest()


class GroupLeakageControls(unittest.TestCase):
    def test_paired_seeds(self):
        outcomes = [evaluate(s)[0] for s in range(100)]
        row = sum(r['row_split']['accuracy'] for r in outcomes) / 100
        group = sum(r['group_split']['accuracy'] for r in outcomes) / 100
        baseline = sum(r['baseline']['constant_zero_group_accuracy'] for r in outcomes) / 100
        self.assertGreater(row, 0.95)
        self.assertLess(abs(group - baseline), 0.0000001)
        self.assertLess(abs(group - 0.5), 0.06)
        self.assertEqual(0, max(r['group_split']['seen_fraction'] for r in outcomes))
        self.assertGreater(min(r['row_split']['seen_fraction'] for r in outcomes), 0.95)

    def test_restart_receipt(self):
        result, digest = evaluate(19)
        loaded = json.loads(json.dumps(result))
        canonical = json.dumps(loaded, sort_keys=True, separators=(',', ':'))
        self.assertEqual(digest, hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual((result, digest), evaluate(19))

    def test_tampering_detected(self):
        result, digest = evaluate(4)
        result['group_split']['accuracy'] = 1.0
        self.assertNotEqual(digest, hashlib.sha256(json.dumps(result, sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def test_bad_design(self):
        for kwargs in ({'groups': 2}, {'repeats': 1}, {'train_fraction': 1.0}):
            with self.assertRaises(ValueError):
                evaluate(0, **kwargs)


if __name__ == '__main__':
    unittest.main()
