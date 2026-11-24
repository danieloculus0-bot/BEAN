import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bean.runtime.workflow_discovery import discover_verified_workflow


class WorkflowDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'memory.sqlite'
        self.conn = sqlite3.connect(self.db)
        self.conn.executescript('''
            CREATE TABLE bean_verified_workflow_trials (
                family TEXT, plan_id TEXT PRIMARY KEY, graph_sha TEXT,
                graph_json TEXT, input_sha TEXT, evidence_json TEXT, passed INTEGER);
            CREATE TABLE cognition_goal_proposals (
                proposal_id TEXT PRIMARY KEY, action_detail TEXT, status TEXT);
        ''')

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def trial(self, pid, family, graph, objective, *, input_sha=None,
              passed=True, provider='local_llamacpp', status='completed'):
        self.conn.execute('INSERT INTO bean_verified_workflow_trials VALUES (?,?,?,?,?,?,?)',
                          (family, pid, graph, '{}', input_sha or pid, '{}', int(passed)))
        detail = {'capability': 'native_orchestration_step', 'objective': objective,
                  'goal_plan': {'id': pid, 'step': 0}, 'planner_provider': provider}
        self.conn.execute('INSERT INTO cognition_goal_proposals VALUES (?,?,?)',
                          (pid, json.dumps(detail), status))
        self.conn.commit()

    def candidates(self, family):
        rows = self.conn.execute('''SELECT graph_sha FROM bean_verified_workflow_trials
            WHERE family=? GROUP BY graph_sha
            HAVING COUNT(DISTINCT CASE WHEN passed=1 THEN input_sha END)>=2
            AND SUM(CASE WHEN passed=0 THEN 1 ELSE 0 END)=0''', (family,))
        return [{'graph_sha': row[0]} for row in rows]

    def recall(self, objective):
        return discover_verified_workflow(self.conn, objective, self.candidates)

    def learned(self, family='assignment', graph='g1', objective='Assign tasks'):
        self.trial(family+'1', family, graph, objective)
        self.trial(family+'2', family, graph, 'Validation', provider='candidate_validation')

    def test_recalls_without_family_after_reopen(self):
        self.learned()
        self.conn.close()
        self.conn = sqlite3.connect(self.db)
        self.assertEqual(self.recall('Assign tasks'), ('assignment', 'g1'))

    def test_unfamiliar_or_similar_objective_abstains(self):
        self.learned()
        self.assertIsNone(self.recall('Assign tasks differently'))
        self.assertIsNone(self.recall('Validation'))

    def test_single_example_or_duplicate_does_not_qualify(self):
        self.trial('one', 'assignment', 'g1', 'Assign tasks', input_sha='same')
        self.trial('two', 'assignment', 'g1', 'Assign tasks', input_sha='same')
        self.assertIsNone(self.recall('Assign tasks'))

    def test_negative_feedback_revokes_recall(self):
        self.learned()
        self.trial('bad', 'assignment', 'g1', 'Assign tasks', passed=False)
        self.assertIsNone(self.recall('Assign tasks'))

    def test_ambiguous_families_abstain(self):
        self.learned()
        self.learned('other', 'g2')
        self.assertIsNone(self.recall('Assign tasks'))

    def test_unrelated_verified_graph_not_selected(self):
        self.learned()
        self.learned('other', 'g2', 'Estimate values')
        self.assertEqual(self.recall('Assign tasks'), ('assignment', 'g1'))
        self.assertEqual(self.recall('Estimate values'), ('other', 'g2'))

    def test_uncompleted_goal_not_evidence_of_objective(self):
        self.trial('one', 'assignment', 'g1', 'Assign tasks', status='failed')
        self.trial('two', 'assignment', 'g1', 'Validation', provider='candidate_validation')
        self.assertIsNone(self.recall('Assign tasks'))


if __name__ == '__main__':
    unittest.main()
