import unittest
from .accounting import chat_tokens, verify_answer_accounting

class Tokenizer:
    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        assert tokenize and add_generation_prompt
        return list(range(len(messages[0]['content'].split()) + 7))

class TestAccounting(unittest.TestCase):
    def test_matching(self):
        t = Tokenizer()
        def answer(prompt, tokens):
            self.assertEqual(tokens, 1)
            return {'tokens_in': chat_tokens(t, prompt)}
        receipts = verify_answer_accounting(t, answer, 32768, 256)
        self.assertEqual(len(receipts), 3)
        self.assertTrue(all(r['actual'] == r['expected'] for r in receipts))
    def test_mismatch(self):
        t = Tokenizer()
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            verify_answer_accounting(t, lambda p,n: {'tokens_in':chat_tokens(t,p)+1}, 32768, 256)
    def test_overflow(self):
        t = Tokenizer()
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            verify_answer_accounting(t, lambda p,n: {'tokens_in':chat_tokens(t,p)}, 10, 256)

if __name__ == '__main__':
    unittest.main()
