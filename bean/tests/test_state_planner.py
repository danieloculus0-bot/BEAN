import random
import unittest
from bean.learning.state_planner import plan_state

def action(name,before,after,cost):
    return {"name":name,"requires":{"present":[before],"absent":[]},"adds":[after],"removes":[before],"cost":cost}

class StatePlannerTests(unittest.TestCase):
    def test_cheaper_longer_route(self):
        r=plan_state(facts=["A","B","C"],initial=["A"],goal={"present":["C"],"absent":["A"]},
            actions=[action("direct","A","C",10),action("first","A","B",2),action("second","B","C",3)])
        self.assertEqual(r["actions"],["first","second"])
        self.assertEqual(r["total_cost"],5)
        self.assertFalse(r["execution_authorized"])

    def test_random_graph_against_floyd_warshall(self):
        rng=random.Random(7226)
        for n in range(3,9):
            labels=[str(i) for i in range(n)]
            for _ in range(25):
                d=[[0 if i==j else float("inf") for j in range(n)] for i in range(n)]
                acts=[]
                for i in range(n):
                    for j in range(n):
                        if i!=j and rng.random()<0.30:
                            w=rng.randint(1,30);d[i][j]=w;acts.append(action(str(i)+"_"+str(j),str(i),str(j),w))
                for k in range(n):
                    for i in range(n):
                        for j in range(n):
                            d[i][j]=min(d[i][j],d[i][k]+d[k][j])
                r=plan_state(facts=labels,initial=["0"],goal={"present":[str(n-1)],"absent":[]},actions=acts)
                if d[0][-1]==float("inf"):
                    self.assertEqual(r["verdict"],"unreachable")
                else:
                    self.assertEqual(r["verdict"],"solved")
                    self.assertEqual(r["total_cost"],d[0][-1])

    def test_negative_precondition_and_unreachable(self):
        a=action("go","A","B",1);a["requires"]["absent"]=["lock"]
        args={"facts":["A","B","lock"],"initial":["A","lock"],"goal":{"present":["B"],"absent":[]},"actions":[a]}
        self.assertEqual(plan_state(**args)["verdict"],"unreachable")
        args["actions"].append({"name":"unlock","requires":{"present":["lock"],"absent":[]},"adds":[],"removes":["lock"],"cost":2})
        self.assertEqual(plan_state(**args)["actions"],["unlock","go"])
        self.assertEqual(plan_state(**args,node_limit=1)["verdict"],"unknown")
