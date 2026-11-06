"""Synthetic negative control: a self-hashed audit receipt is not authenticated.

A trusted digest checkpoint external to an attacker-controlled receipt is needed
for tamper evidence. This is NOT a signature, identity proof, or deployed BEAN
journal. The anchor must be stored outside the adversary's write scope.
"""
import copy
import hashlib
import json
import unittest


def digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def receipt(state):
    return {'state': copy.deepcopy(state), 'sha256': digest(state)}


def self_check(record):
    return record['sha256'] == digest(record['state'])


def anchored_check(record, trusted_digest):
    return self_check(record) and record['sha256'] == trusted_digest


class AnchorControls(unittest.TestCase):
    def test_forged_self_hash_passes_without_anchor(self):
        original = receipt({'schema': 1, 'n': 100, 'errors': 20})
        forged = receipt({'schema': 1, 'n': 100, 'errors': 0})
        self.assertTrue(self_check(original))
        self.assertTrue(self_check(forged))
        self.assertNotEqual(original['sha256'], forged['sha256'])
        self.assertFalse(anchored_check(forged, original['sha256']))
        self.assertTrue(anchored_check(original, original['sha256']))

    def test_bit_flip_without_rehash_is_detected(self):
        original = receipt({'schema': 1, 'n': 100, 'errors': 20})
        changed = copy.deepcopy(original)
        changed['state']['errors'] = 0
        self.assertFalse(self_check(changed))

    def test_anchor_survives_serialization_restart(self):
        state = {'schema': 1, 'n': 100, 'errors': 20}
        original = receipt(state)
        trusted = original['sha256']
        restored = json.loads(json.dumps(original))
        self.assertTrue(anchored_check(restored, trusted))
        restored['state']['errors'] = 0
        restored['sha256'] = digest(restored['state'])
        self.assertFalse(anchored_check(restored, trusted))

    def test_anchor_itself_compromised_is_not_protection(self):
        forged = receipt({'schema': 1, 'n': 100, 'errors': 0})
        self.assertTrue(anchored_check(forged, forged['sha256']))
        # A compromised anchor cannot attest to genuine observations.

    def test_deterministic_fixed_budget(self):
        states = [{'schema': 1, 'n': i, 'errors': i // 5} for i in range(1, 501)]
        hashes = [digest(s) for s in states]
        self.assertEqual(hashes, [digest(s) for s in states])
        self.assertEqual(len(set(hashes)), 500)


if __name__ == '__main__':
    unittest.main()
