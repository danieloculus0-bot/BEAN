import tempfile
import unittest
from pathlib import Path
from switch_puzzle import State, move, optimal, QBean, frozen_evaluate, run

class TestPuzzle(unittest.TestCase):
    def test_brute_force_reaches_every_state(self):
        for target in range(8):
            for bits in range(8):
                for cursor in range(3):
                    state=State(bits,cursor,target)
                    for action in optimal(state):state=move(state,action)
                    self.assertEqual(state.bits,target)
    def test_learning_and_scoreboard(self):
        bean,report=run(seed=17,episodes=9000)
        self.assertEqual(report['brute_force_oracle_cases'],192)
        self.assertGreater(bean.updates,0)
        self.assertGreater(report['q_learning']['solved'],report['baseline']['solved'])
        self.assertGreater(report['q_learning']['average_reward'],report['baseline']['average_reward'])
    def test_policy_survives_restart(self):
        bean,report=run(seed=17,episodes=9000)
        before=frozen_evaluate(bean)
        with tempfile.TemporaryDirectory() as work:
            path=Path(work)/'policy.gz'
            digest=bean.save(path)
            other=QBean().load(path,digest)
            self.assertEqual(frozen_evaluate(other),before)
            path.write_bytes(path.read_bytes()[:-3]+b'bad')
            with self.assertRaises((ValueError,EOFError,OSError)):
                QBean().load(path,digest)

if __name__=='__main__':unittest.main()
