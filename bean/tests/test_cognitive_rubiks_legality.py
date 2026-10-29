"""Independent legal-state checks for BEAN's learned 3x3 policies."""
import unittest

from experiments.cognitive_gauntlet.rubiks3 import SOLVED, apply, scramble
from experiments.cognitive_gauntlet.rubiks3_legality import (
    CENTERS, CORNERS, EDGES, validate_legal_cube,
)
from experiments.cognitive_gauntlet.rubiks3_sponge import policy_solve
from experiments.cognitive_gauntlet.rubiks3_symmetry import (
    policy_solve_symmetric, transform,
)


class CubeLegalityTests(unittest.TestCase):
    def test_legal_scrambles_and_all_rotations(self):
        for seed in range(40):
            state = apply(SOLVED, scramble(seed, 40))
            for rotation in range(24):
                validate_legal_cube(transform(state, rotation))

    def test_center_swap_rejected(self):
        state = list(SOLVED)
        a, b = CENTERS[:2]
        state[a], state[b] = state[b], state[a]
        with self.assertRaisesRegex(ValueError, 'center'):
            validate_legal_cube(''.join(state))

    def test_single_edge_flip_rejected(self):
        state = list(SOLVED)
        a, b = EDGES[0]
        state[a], state[b] = state[b], state[a]
        with self.assertRaisesRegex(ValueError, 'edge flip'):
            validate_legal_cube(''.join(state))

    def test_single_corner_twist_rejected(self):
        state = list(SOLVED)
        a, b, c = CORNERS[0]
        state[a], state[b], state[c] = state[c], state[a], state[b]
        with self.assertRaisesRegex(ValueError, 'corner twist'):
            validate_legal_cube(''.join(state))

    def test_two_edge_cubies_swap_rejected(self):
        state = list(SOLVED)
        for a, b in zip(EDGES[0], EDGES[1]):
            state[a], state[b] = state[b], state[a]
        with self.assertRaisesRegex(ValueError, 'permutation parity'):
            validate_legal_cube(''.join(state))

    def test_bad_piece_identity_rejected(self):
        state = list(SOLVED)
        a = EDGES[0][0]
        b = next(i for i in CORNERS[0] if SOLVED[i] != SOLVED[a])
        state[a], state[b] = state[b], state[a]
        with self.assertRaises(ValueError):
            validate_legal_cube(''.join(state))

    def test_invalid_input_rejected(self):
        for value in (None, '', SOLVED[:-1], SOLVED.replace('U', 'F', 1)):
            with self.assertRaises(ValueError):
                validate_legal_cube(value)

    def test_both_native_policies_reject_illegal_cube(self):
        state = list(SOLVED)
        a, b = EDGES[0]
        state[a], state[b] = state[b], state[a]
        impossible = ''.join(state)
        for policy in (policy_solve, policy_solve_symmetric):
            with self.subTest(policy=policy.__name__):
                with self.assertRaisesRegex(ValueError, 'edge flip'):
                    policy(object(), impossible)


if __name__ == '__main__':
    unittest.main()
