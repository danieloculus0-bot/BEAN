import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path
from bean.optimization.autodev import Journal
if find_spec("torch"):
    from bean.optimization.sponge_dqn import SpongeDQN
else:SpongeDQN=None

@unittest.skipUnless(SpongeDQN is not None,"Optional PyTorch research dependency absent")
class DQNDomainRetentionTests(unittest.TestCase):
    def test_real_gradient_update_and_full_restart_continuation(self):
        import torch
        torch.set_num_threads(1)
        agent=SpongeDQN(seed=7,observation_size=4,actions=("cash","trend","revert"),domain="market",batch_size=4,warmup=4,learn_every=1,target_sync=3,replay_capacity=32)
        before=agent.weights_digest()
        for i in range(20):agent.observe([i/20,0.2,0.1,1],i%3,(-1)**i*.2,[(i+1)/20,.2,.1,1],False)
        self.assertNotEqual(before,agent.weights_digest());self.assertGreater(agent.updates,0)
        with tempfile.TemporaryDirectory() as folder:
            with_journal=Journal(Path(folder)/"learning.sqlite3")
            agent.checkpoint(with_journal,baseline=0,candidate=-.2,samples=30,evaluation_sha256="a"*64,episode="development",metadata={"negative_result_retained":True})
            with_journal.close()
            reopened=Journal(Path(folder)/"learning.sqlite3")
            restored=SpongeDQN.recover_latest(reopened)
            self.assertEqual(agent.training_state(),restored.training_state())
            self.assertEqual(agent.choose([.2,.1,.3,1],epsilon=.2),restored.choose([.2,.1,.3,1],epsilon=.2))
            args=([.2,.1,.3,1],1,.05,[.3,.1,.3,1],False)
            self.assertEqual(agent.observe(*args),restored.observe(*args))
            self.assertEqual(agent.weights_digest(),restored.weights_digest())
            self.assertEqual(agent.training_state(),restored.training_state());reopened.close()

    def test_frozen_inference_does_not_change_weights(self):
        m=SpongeDQN(observation_size=4,actions=("cash","long"),domain="market")
        prior=m.weights_digest()
        for _ in range(10):m.choose([1,2,3,4],epsilon=0)
        self.assertEqual(prior,m.weights_digest());self.assertEqual(m.updates,0)

    def test_dimensions_finiteness_and_legacy_encoder(self):
        m=SpongeDQN(observation_size=4,actions=("cash","long"))
        with self.assertRaises(ValueError):m.choose([1,2,3])
        with self.assertRaises(ValueError):m.choose([1,2,3,float("nan")])
        old=SpongeDQN();self.assertEqual(old.encode([7,0,1]),(0,0,1))

    def test_tabular_frozen_inference_does_not_insert_unknown_states(self):
        from bean.optimization.sponge_td import SpongeTD
        with tempfile.TemporaryDirectory() as folder:
            p=SpongeTD(Path(folder)/"td.sqlite3",actions=("cash","long"))
            self.assertEqual(p.choose(["unseen"],explore=False),0)
            self.assertEqual(p.q,{})
            p.close()

if __name__=="__main__":unittest.main()
