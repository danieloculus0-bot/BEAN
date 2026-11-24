import unittest
from .runner import run_question, select_ids, TYPES, fit

def question(i):
    return {"question_id":str(i),"question_type":"single-session-user",
            "question":"What is my pet?", "question_date":"2026-01-02",
            "answer":"cat","haystack_dates":["2026-01-01","2026-01-02"],
            "haystack_session_ids":["answer_secret","noise"],
            "haystack_sessions":[[{"role":"user","content":"My pet is a cat.","has_answer":True}],
                                 [{"role":"assistant","content":"Okay."}]],
            "answer_session_ids":["answer_secret"]}

class TestHarness(unittest.TestCase):
    def test_three_questions_all_arms(self):
        calls=[]
        def answer(prompt,n):
            self.assertNotIn("answer_secret",prompt)
            self.assertNotIn("has_answer",prompt)
            calls.append(prompt)
            return {"text":"cat","tokens_in":len(prompt.split()),"tokens_out":1}
        def judge(prompt,n):
            self.assertEqual(n,10)
            self.assertNotIn("Arm:",prompt)
            return {"text":"yes"}
        retrieve=lambda history,q: history[:1]
        for i in range(3):
            for arm in ("A0","A1","A2","A3","A4"):
                row=run_question(question(i),arm,answer,judge,lambda x:len(x.split()),
                    bean=retrieve,hindsight=retrieve,shuffled=question((i+1)%3))
                self.assertTrue(row["judge_verdict"])
                self.assertEqual(row["question_id"],str(i))
                self.assertEqual(len(row["retrieved_context_sha256"]),64)
        self.assertEqual(len(calls),15)

    def test_fixed_disjoint_stratification(self):
        rows=[{"question_id":f"{t}:{i}","question_type":t} for t in TYPES for i in range(20)]
        a=select_ids(rows,20261124)
        b=select_ids(rows,20261125,exclude=a)
        self.assertEqual(len(a),50)
        self.assertEqual(a,select_ids(list(reversed(rows)),20261124))
        self.assertFalse(set(a)&set(b))

    def test_token_budget(self):
        self.assertEqual(fit(["a b","c d"],lambda x:len(x.split()),2),"a b")
        self.assertEqual(fit(["a b","c d"],lambda x:len(x.split()),2,recent=True),"c d")

if __name__=="__main__":
    unittest.main()
