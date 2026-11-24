"""Bounded cost-optimal planning over a host-supplied symbolic transition model.

Dijkstra over finite boolean states (classical planning with positive/negative
preconditions). Produces digital plans only, never executes external actions.
"""
from heapq import heappop, heappush
from itertools import count


def plan_state(*, facts, initial, goal, actions, node_limit=20000):
    def names(values, label):
        if not isinstance(values,list) or len(values)>64 or any(not isinstance(v,str) or not 1<=len(v)<=80 for v in values) or len(set(values))!=len(values):
            raise ValueError("invalid "+label)
        return frozenset(values)
    universe=names(facts,"facts")
    if not universe:raise ValueError("facts required")
    start=names(initial,"initial")
    if not start<=universe:raise ValueError("unknown initial facts")
    def condition(obj):
        if not isinstance(obj,dict) or set(obj)!={"present","absent"}:raise ValueError("condition requires present and absent")
        yes,no=names(obj["present"],"present"),names(obj["absent"],"absent")
        if yes&no or not yes|no<=universe:raise ValueError("invalid condition facts")
        return yes,no
    wanted,excluded=condition(goal)
    if type(node_limit) is not int or not 1<=node_limit<=100000:raise ValueError("invalid search limit")
    if not isinstance(actions,list) or len(actions)>128:raise ValueError("invalid action list")
    parsed=[];seen=set()
    for a in actions:
        if not isinstance(a,dict) or set(a)!={"name","requires","adds","removes","cost"}:raise ValueError("invalid action")
        name=a["name"];cost=a["cost"]
        if not isinstance(name,str) or not 1<=len(name)<=80 or name in seen:raise ValueError("invalid action name")
        if type(cost) is not int or not 1<=cost<=1000000:raise ValueError("positive bounded integer cost required")
        seen.add(name)
        yes,no=condition(a["requires"])
        adds,removes=names(a["adds"],"adds"),names(a["removes"],"removes")
        if adds&removes or not adds|removes<=universe:raise ValueError("invalid effects")
        parsed.append((name,yes,no,adds,removes,cost))
    parsed.sort()
    def satisfied(s):return wanted<=s and not excluded&s
    serial=count();queue=[(0,next(serial),start)]
    costs={start:0};parent={};expanded=0
    def report(verdict,**kwargs):
        return {"status":"success" if verdict!="unknown" else "unknown","verdict":verdict,"expanded":expanded,
                "execution_authorized":False,"scope":"supplied_digital_transition_model",**kwargs}
    while queue:
        cost,_,state=heappop(queue)
        if costs[state]!=cost:continue
        if satisfied(state):
            route=[];states=[sorted(state)]
            cur=state
            while cur!=start:
                prev,name=parent[cur];route.append(name);states.append(sorted(prev));cur=prev
            return report("solved",actions=list(reversed(route)),states=list(reversed(states)),total_cost=cost,optimal=True)
        if expanded>=node_limit:return report("unknown",reason="node_limit",optimal=False)
        expanded+=1
        for name,yes,no,adds,removes,weight in parsed:
            if not yes<=state or no&state:continue
            nxt=(state-removes)|adds
            total=cost+weight
            if total>=costs.get(nxt,float("inf")):continue
            # Also bound the number of discovered states, not just expansions.
            if nxt not in costs and len(costs)>=node_limit+1:
                return report("unknown",reason="state_limit",optimal=False)
            costs[nxt]=total;parent[nxt]=(state,name)
            heappush(queue,(total,next(serial),nxt))
    return report("unreachable",optimal=True)
