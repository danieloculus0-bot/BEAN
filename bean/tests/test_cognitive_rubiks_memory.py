"""Behavioral checks for case-based 3x3 cube skill learning."""
import unittest
from experiments.cognitive_gauntlet.rubiks3 import SOLVED,apply,invert
from experiments.cognitive_gauntlet.rubiks3_memory import RouteMemory,experiment

class CubeMemoryTests(unittest.TestCase):
    def test_failed_demonstrations_not_learned(self):
        memory=RouteMemory()
        state=apply(SOLVED,['R','U'])
        self.assertEqual(memory.observe(state,['F']),0)
        self.assertEqual(memory.routes,{})
        self.assertEqual(memory.accepted,0)

    def test_verified_route_transfers_to_unseen_neighbor(self):
        memory=RouteMemory()
        training=apply(SOLVED,['R','U','F'])
        training_answer=invert(['R','U','F'])
        self.assertGreater(memory.observe(training,training_answer),0)
        holdout=apply(training,['L'])
        self.assertNotIn(holdout,memory.routes)
        answer=memory.propose(holdout,lookahead=1)
        self.assertIsNotNone(answer)
        self.assertEqual(apply(holdout,answer),SOLVED)
        self.assertEqual(len(answer),4)

    def test_only_replace_with_shorter_valid_route(self):
        memory=RouteMemory()
        pos=apply(SOLVED,['R'])
        memory.observe(pos,["R'"])
        memory.observe(pos,['U',"U'","R'"])
        self.assertEqual(memory.routes[pos],("R'",))

    def test_seed_isolation_and_determinism(self):
        a=experiment(train_seeds=range(2),test_seeds=range(30,32),lengths=(3,4))
        b=experiment(train_seeds=range(2),test_seeds=range(30,32),lengths=(3,4))
        self.assertEqual(a,b)
        self.assertEqual(len(a['holdout']),4)
        self.assertTrue(all(c['candidate_solved'] or c['selected'] is None for c in a['holdout']))
        with self.assertRaises(ValueError):
            experiment(train_seeds=[3],test_seeds=[3])

if __name__=='__main__':unittest.main()
