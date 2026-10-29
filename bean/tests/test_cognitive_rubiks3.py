"""Independent contract tests for the Gauntlet 3x3 bounded search."""
import unittest
from experiments.cognitive_gauntlet.rubiks3 import (
    FACES, MOVES, SOLVED, apply, invert, scramble, solve, run_cases,
)

class CubeTests(unittest.TestCase):
    def test_move_group(self):
        for move in MOVES:
            self.assertEqual(apply(SOLVED,[move]+invert([move])),SOLVED)
        for face in FACES:
            self.assertEqual(apply(SOLVED,[face]*4),SOLVED)
            self.assertEqual(apply(SOLVED,[face+'2']*2),SOLVED)

    def test_sexy_move_order_six(self):
        self.assertEqual(apply(SOLVED,['R','U',"R'","U'"]*6),SOLVED)

    def test_color_counts_and_centers(self):
        state=apply(SOLVED,scramble(357,40))
        for face in FACES:
            self.assertEqual(state.count(face),9)
        self.assertEqual(''.join(state[i*9+4] for i in range(6)), FACES)

    def test_optimality_and_shorter_than_recipe(self):
        for seq in (['R'],['R','L',"R'"],['R','U','F'],['R','L',"R'","L'"]):
            state=apply(SOLVED,seq)
            sol,meta=solve(state)
            self.assertTrue(meta['optimal_within_depth'])
            self.assertEqual(apply(state,sol),SOLVED)
            self.assertLessEqual(len(sol),len(seq))
        state=apply(SOLVED,['R','L',"R'"])
        sol,_=solve(state)
        self.assertEqual(len(sol),1)

    def test_unsolved_limit_not_proof_unsolvable(self):
        state=apply(SOLVED,['R','U','F'])
        solution,meta=solve(state,max_depth=2)
        self.assertIsNone(solution)
        self.assertTrue(meta['complete'])
        self.assertFalse(meta['optimal_within_depth'])

    def test_seed_determinism_and_receipts(self):
        a=run_cases(range(2),lengths=(3,4))
        b=run_cases(range(2),lengths=(3,4))
        self.assertEqual(a,b)
        self.assertEqual(4,len(a['cases']))
        self.assertTrue(all(c['solved'] for c in a['cases']))
        for case in a['cases']:
            self.assertEqual(apply(case['state'],case['solution']),SOLVED)

if __name__=='__main__':
    unittest.main()
