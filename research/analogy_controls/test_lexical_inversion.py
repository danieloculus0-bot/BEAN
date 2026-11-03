"""Synthetic falsification control for lexical precedent transfer.

Research-only: does not run BEAN, change policy, or validate real transfer.
Run: python -m unittest discover -s research/analogy_controls -p 'test_*.py'
"""
import re
import unittest

def tokens(text):
    return set(re.findall(r"[a-z]+", text.lower()))

def lexical_overlap(source, query):
    return len(tokens(source) & tokens(query))

class CausalInversionNegativeControl(unittest.TestCase):
    def test_equal_words_opposite_direction(self):
        # The same words express opposite causal directions. A bag-of-words
        # precedent selector cannot discriminate them, even with perfect recall.
        query = "valve open causes pressure rise"
        supporting = "valve open causes pressure rise"
        contradictory = "pressure rise causes valve open"
        self.assertEqual(lexical_overlap(supporting, query),
                         lexical_overlap(contradictory, query))
        self.assertNotEqual(supporting, contradictory)

    def test_negation_lexical_trap(self):
        # A more overlapping precedent can be explicitly negative evidence.
        query = "coolant flow improves temperature stability"
        supporting = "coolant improves stability"
        negative = "coolant flow does not improve temperature stability"
        self.assertGreater(lexical_overlap(negative, query),
                           lexical_overlap(supporting, query))
        self.assertIn("not", tokens(negative))

if __name__ == "__main__":
    unittest.main()
