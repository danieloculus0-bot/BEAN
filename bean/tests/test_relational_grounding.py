import unittest
from bean.learning.relational_grounding import infer_relations


class RelationTransferTests(unittest.TestCase):
    def test_same_composition_transfers_between_domains(self):
        for a, b, c in [('pump', 'valve', 'tank'), ('module_a', 'module_b', 'module_c'),
                        ('robot_cell', 'corridor', 'charging_station')]:
            with self.subTest(a=a):
                r = infer_relations(facts=[[a, 'connects', b, 'obs1'], [b, 'connects', c, 'obs2'],
                                           ['unrelated', 'connects', c, 'obs3']],
                                    patterns=[['?a', 'connects', '?b'], ['?b', 'connects', '?c']],
                                    conclusion=['?a', 'two_hop_connection', '?c'])
                self.assertEqual(r['inferences'], [{'relation': [a, 'two_hop_connection', c],
                                                      'evidence_sets': [['obs1', 'obs2']]}])

    def test_missing_link_abstains(self):
        r = infer_relations(facts=[['a', 'edge', 'b', '1']],
                            patterns=[['?a', 'edge', '?b'], ['?b', 'edge', '?c']],
                            conclusion=['?a', 'reachable', '?c'])
        self.assertEqual((r['status'], r['count']), ('unknown', 0))

    def test_unbound_conclusion_rejected(self):
        with self.assertRaises(ValueError):
            infer_relations(facts=[], patterns=[['?a', 'edge', '?b']], conclusion=['?a', 'edge', '?c'])

    def test_repeated_variable_requires_same_value(self):
        r = infer_relations(facts=[['a', 'edge', 'b', '1'], ['c', 'edge', 'c', '2']],
                            patterns=[['?a', 'edge', '?a']], conclusion=['?a', 'self_edge', '?a'])
        self.assertEqual(r['inferences'][0]['relation'], ['c', 'self_edge', 'c'])


if __name__ == '__main__':
    unittest.main()
