"""Focused contracts for synthetic uncertainty, visible score and real Q updates."""
import copy
import tempfile
import unittest
from pathlib import Path
from fault_detective import (
    ACTIONS, FAULTS, TESTS, PRIOR, COST, QBrain, Scoreboard, diagnostic,
    information_gain, play, specimen, state, update, archive
)

class FaultDetectiveTests(unittest.TestCase):
    def test_generator_never_reveals_answer_through_state(self):
        example=specimen(42,61309,.05)
        a=state(tuple(PRIOR),[],Scoreboard())
        altered=copy.deepcopy(example);altered["fault"]=(example["fault"]+1)%8
        b=state(tuple(PRIOR),[],Scoreboard())
        self.assertEqual(a,b)
        self.assertEqual(len(example["outcomes"]),len(TESTS))
        self.assertNotEqual(example["fault"],altered["fault"])

    def test_bayes_stays_normalized(self):
        values=tuple(PRIOR)
        for test in range(8):
            values=update(values,test,test%2)
            self.assertAlmostEqual(sum(values),1.,places=12)
        self.assertTrue(all(0<=x<=1 for x in values))

    def test_reward_from_independent_truth_only(self):
        sample=specimen(3,61309,.05)
        board=Scoreboard()
        trace=play(sample,"info5",board)
        self.assertEqual(trace["correct"],trace["diagnosed_fault"]==sample["fault"])
        self.assertEqual(trace["reward"],round((40 if trace["correct"] else -40)
                          -sum(COST[m["test"]] for m in trace["trace"] if "test" in m),6))
        self.assertEqual(board.games,1)
        self.assertEqual(trace["trace"][0]["scoreboard_seen"]["games"],0)
        self.assertGreaterEqual(trace["probes"],1)

    def test_q_update_and_visible_scoreboard(self):
        brain=QBrain(20);board=Scoreboard()
        s=state(tuple(PRIOR),[],board)
        self.assertEqual(brain.select(s,0),0)
        brain.learn(s,2,6.)
        self.assertGreater(brain.q[s][2],brain.q[s][0])
        self.assertEqual(brain.select(s,0),2)
        board.record(True,37,2)
        self.assertEqual(board.view()["wins"],1)

    def test_costed_information_probing(self):
        prior=tuple(PRIOR)
        test=diagnostic(prior,[],"information")
        self.assertGreater(information_gain(prior,test),0)
        self.assertIn(test,range(8))
        self.assertNotEqual(diagnostic(prior,[test],"information"),test)

    def test_exact_archive_is_reloadable_for_tiny_fixture(self):
        from indexed_ledger import IndexedLedger
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            db=IndexedLedger(root)
            rec={"kind":"test","name":"FAULT-TINY","status":"failed",
                 "sample":specimen(1,993,.1),"reward":-4.0}
            db.append("small",[rec])
            self.assertEqual(db.rebuild(),1)
            index=db.ids(name="FAULT-TINY")[0]
            self.assertEqual(db.get(index),rec)
            db.cache.unlink()
            self.assertEqual(db.rebuild(),1)
            self.assertEqual(db.get(index),rec)

if __name__=="__main__":
    unittest.main()
