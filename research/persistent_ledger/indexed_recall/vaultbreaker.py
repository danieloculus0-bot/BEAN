"""BEAN vs Vaultbreaker: brute-force deduction, visible scoreboard and neural tactic selection.

Synthetic research sandbox. Independent oracle owns hidden code; agent receives
only feedback. Every guess, score view and reward is archived losslessly with
the existing indexed/compressed research ledger.
"""
from __future__ import annotations
import argparse
import base64
import copy
import itertools
import json
import math
import random
from collections import Counter
from pathlib import Path

from indexed_ledger import IndexedLedger, encode, sha

CODES = tuple(itertools.product(range(6), repeat=4))
TACTICS = ('first', 'minimax', 'entropy')
MAX_TURNS = 9


def feedback(code: tuple[int, ...], guess: tuple[int, ...]) -> tuple[int, int]:
    exact = sum(a == b for a, b in zip(code, guess))
    matched = sum((Counter(code) & Counter(guess)).values())
    return exact, matched - exact


class Vault:
    """Truth holder; only feedback is available to the solver."""
    def __init__(self, secret: tuple[int, ...]):
        if secret not in CODES:
            raise ValueError('invalid secret')
        self._secret = secret

    def try_code(self, guess: tuple[int, ...]) -> tuple[int, int]:
        if guess not in CODES:
            raise ValueError('invalid guess')
        return feedback(self._secret, guess)


def _tactic(pool: tuple, name: str, history: list, budget: int = 28) -> tuple[tuple, int]:
    """Brute-force compatible codes; compare reproducible bounded probes."""
    if name == 'first' or len(pool) == 1:
        return pool[0], 0
    size = len(pool)
    probes = pool if size <= budget else tuple(pool[(i*(size-1))//(budget-1)] for i in range(budget))
    best_guess, best_score = None, None
    checks = 0
    for guess in probes:
        groups: dict[tuple[int, int], int] = {}
        for potential in pool:
            key = feedback(potential, guess)
            groups[key] = groups.get(key, 0) + 1
            checks += 1
        score = max(groups.values()) if name == 'minimax' else sum(n*n for n in groups.values())
        if best_score is None or (score, guess) < (best_score, best_guess):
            best_guess, best_score = guess, score
    return best_guess, checks


def reward(before: int, after: int, solved: bool, checks: int) -> float:
    """Host-verified reward; information term telescopes, preventing turn farming."""
    return round(10*math.log2(before/after) - 9 - .00002*checks + (100 if solved else 0), 5)


def _input(board: dict, candidates: int, turn: int, live_reward: float = 0) -> list[float]:
    return [1.0, math.log2(candidates)/math.log2(len(CODES)),
            turn/MAX_TURNS, board['wins']/max(1,board['games']),
            max(-1.0, min(1.0,(board['reward_total']/max(1,board['games'])+live_reward)/120))]


class TinyNeuralPolicy:
    """Actual 5->8->3 trainable neural policy, dependency-free."""
    def __init__(self, seed: int = 2026, state: dict | None = None):
        if state:
            if state.get('schema') != 'bean.vault.net.v1':
                raise ValueError('network state schema mismatch')
            self.w1 = state['w1']
            self.w2 = state['w2']
            self.updates = state['updates']
        else:
            rng = random.Random(seed)
            self.w1 = [[rng.uniform(-.2,.2) for _ in range(5)] for _ in range(8)]
            self.w2 = [[rng.uniform(-.2,.2) for _ in range(9)] for _ in TACTICS]
            self.updates = 0

    def state(self) -> dict:
        return {'schema':'bean.vault.net.v1','w1':self.w1,'w2':self.w2,'updates':self.updates}

    def digest(self) -> str:
        return sha(encode(self.state()))

    def predict(self, inputs: list[float]):
        hidden = [math.tanh(sum(a*b for a,b in zip(row,inputs))) for row in self.w1]
        expanded = hidden + [1.0]
        scores = [sum(a*b for a,b in zip(row,expanded)) for row in self.w2]
        return hidden, scores

    def select(self, inputs: list[float], episode: int, turn: int, *, explore: bool) -> str:
        if explore and (episode+turn)%5 == 0:
            return TACTICS[(episode+turn)%len(TACTICS)]
        _, predictions = self.predict(inputs)
        return TACTICS[max(range(3),key=lambda i:(predictions[i],-i))]

    def learn(self, inputs: list[float], tactic: str, observed_reward: float, lr: float = .025):
        hidden, outputs = self.predict(inputs)
        index = TACTICS.index(tactic)
        err = max(-2.0,min(2.0,observed_reward/100-outputs[index]))
        old = self.w2[index][:]
        expanded = hidden+[1.0]
        for i in range(9):
            self.w2[index][i] += lr*err*expanded[i]
        for i in range(8):
            grad = lr*err*old[i]*(1-hidden[i]**2)
            for j in range(5):
                self.w1[i][j] += grad*inputs[j]
        self.updates += 1


def initial_board():
    return {'schema':'bean.vault.scoreboard.v1','games':0,'wins':0,'reward_total':0.0,
            'total_guesses':0,'tactics':{t:{'turns':0,'reward':0.0} for t in TACTICS}}


def play(secret: tuple[int, ...], policy: TinyNeuralPolicy | None, board: dict, *,
         episode: int, train: bool = False) -> dict:
    oracle = Vault(secret)
    candidates = CODES
    moves = []
    history = []
    for turn in range(1,MAX_TURNS+1):
        score_view = copy.deepcopy(board)
        live_reward=round(sum(x['reward'] for x in moves),5)
        score_view['live'] = {'episode':episode,'turn':turn,'remaining':len(candidates),
                              'reward_so_far':live_reward}
        view_hash = sha(encode(score_view))
        features = _input(board,len(candidates),turn,live_reward)
        weights_before = policy.digest() if policy else None
        tactic = policy.select(features,episode,turn,explore=train) if policy else 'first'
        guess, checks = _tactic(candidates,tactic,history)
        observed = oracle.try_code(guess)
        remaining = tuple(c for c in candidates if feedback(c,guess)==observed)
        solved = observed[0] == 4
        earned = reward(len(candidates),len(remaining),solved,checks)
        move = {'turn':turn,'tactic':tactic,'guess':list(guess),'feedback':list(observed),
                'remaining_before':len(candidates),'remaining_after':len(remaining),
                'evaluations':checks,'reward':earned,'scoreboard_seen':score_view,
                'scoreboard_seen_sha256':view_hash,'weights_before_sha256':weights_before}
        moves.append(move)
        history.append((guess,observed))
        if policy and train:
            policy.learn(features,tactic,earned)
        candidates=remaining
        if not candidates:
            raise AssertionError('oracle feedback eliminated its secret')
        if solved:
            break
    won = moves[-1]['feedback'][0] == 4
    trace={'schema':'bean.vault.episode.v1','episode':episode,
           'secret_revealed_after':list(secret),'moves':moves,'won':won,
           'turns':len(moves),'reward_total':round(sum(m['reward'] for m in moves)-(0 if won else 100),5)}
    board['games'] += 1
    board['wins'] += int(won)
    board['total_guesses'] += len(moves)
    board['reward_total'] = round(board['reward_total']+trace['reward_total'],5)
    for move in moves:
        stat=board['tactics'][move['tactic']]
        stat['turns'] += 1
        stat['reward'] = round(stat['reward']+move['reward'],5)
    return trace


def verify_trace(trace: dict):
    """Re-derive guesses, oracle feedback, reward and score-view identity."""
    secret=tuple(trace['secret_revealed_after'])
    candidates=CODES
    for i,move in enumerate(trace['moves'],1):
        guess=tuple(move['guess'])
        predicted,checks=_tactic(candidates,move['tactic'],trace['moves'][:i-1])
        if guess!=predicted or checks!=move['evaluations'] or guess not in candidates:
            raise AssertionError('illegal or incorrectly reported strategy guess')
        view=move['scoreboard_seen']
        if (view.get('live')!={'episode':trace['episode'],'turn':i,'remaining':len(candidates),
                          'reward_so_far':round(sum(x['reward'] for x in trace['moves'][:i-1]),5)}
            or any(view.get(k)!=trace['moves'][0]['scoreboard_seen'].get(k)
                   for k in ('games','wins','reward_total','total_guesses','tactics'))
            or sha(encode(view))!=move['scoreboard_seen_sha256']):
            raise AssertionError('scoreboard receipt mismatch')
        observed=feedback(secret,guess)
        remaining=tuple(c for c in candidates if feedback(c,guess)==observed)
        earned=reward(len(candidates),len(remaining),observed[0]==4,checks)
        if (move['turn']!=i or move['remaining_before']!=len(candidates)
            or move['remaining_after']!=len(remaining)
            or move['feedback']!=list(observed) or move['reward']!=earned):
            raise AssertionError('oracle replay diverged')
        candidates=remaining
    solved=trace['moves'][-1]['feedback'][0]==4
    if trace['won']!=solved or trace['turns']!=len(trace['moves']):
        raise AssertionError('incorrect win or turn count')
    if trace['reward_total']!=round(sum(m['reward'] for m in trace['moves'])-(0 if solved else 100),5):
        raise AssertionError('incorrect episode reward')


def archive_episode(ledger: IndexedLedger, label: str, trace: dict) -> dict:
    source=encode(trace)
    events=[{'kind':'attachment','name':'game_trace.json','sha256':sha(source),
             'data_b64':base64.b64encode(source).decode('ascii')}]
    for move in trace['moves']:
        events.append({'kind':'attachment','name':f"move-{move['turn']:02d}",'data':move})
    events.append({'kind':'test','name':'vault-cracked','status':'passed' if trace['won'] else 'failed',
                   'reward':trace['reward_total'],'turns':trace['turns']})
    return ledger.append(label,events)


def replay_archive(ledger: IndexedLedger, label: str) -> dict:
    refs=ledger.ids(run=label,name='game_trace.json')
    if len(refs)!=1:
        raise AssertionError('missing or ambiguous original trace')
    original=ledger.get(refs[0])
    raw=base64.b64decode(original['data_b64'],validate=True)
    if sha(raw)!=original['sha256']:
        raise AssertionError('trace attachment corrupt')
    trace=json.loads(raw)
    verify_trace(trace)
    return trace


def batch(secrets: list[tuple], policy: TinyNeuralPolicy | None, folder: Path,
          phase: str, *, train: bool = False) -> dict:
    board=initial_board()
    ledger=IndexedLedger(folder)
    results=[]
    for i,secret in enumerate(secrets):
        trace=play(secret,policy,board,episode=i,train=train)
        verify_trace(trace)
        archive_episode(ledger,f'{phase}-{i:03d}',trace)
        results.append(trace)
    ledger.rebuild()
    for i,trace in enumerate(results):
        if replay_archive(ledger,f'{phase}-{i:03d}')!=trace:
            raise AssertionError('historical retrieval diverged')
    return {'scoreboard':board,'win_rate':board['wins']/max(1,board['games']),
            'mean_turns':round(board['total_guesses']/max(1,board['games']),3),
            'mean_reward':round(board['reward_total']/max(1,board['games']),3),
            'replayed_games':len(results),
            'archive_bytes':sum(p.stat().st_size for p in ledger.archive.iterdir()),
            'index_bytes':ledger.cache.stat().st_size}


def experiment(root: Path, training: int = 36, holdout: int = 18, seed: int = 714) -> dict:
    if training<6 or holdout<6 or training+holdout>len(CODES):
        raise ValueError('invalid train/holdout split')
    rng=random.Random(seed)
    shuffled=list(CODES)
    rng.shuffle(shuffled)
    training_codes, heldout=shuffled[:training],shuffled[training:training+holdout]
    root.mkdir(parents=True,exist_ok=True)
    policy=TinyNeuralPolicy(seed)
    initial_hash=policy.digest()
    trained_games=batch(training_codes,policy,root/'training','training',train=True)
    (root/'neural_state.json').write_bytes(encode(policy.state())+b'\n')
    # Reload learning state cold, freeze all held-out policies.
    recovered=TinyNeuralPolicy(state=json.loads((root/'neural_state.json').read_text()))
    untrained=TinyNeuralPolicy(seed)
    baseline_games=batch(heldout,None,root/'fixed_baseline','baseline')
    cold_games=batch(heldout,untrained,root/'untrained_neural','cold')
    learned_games=batch(heldout,recovered,root/'trained_neural','trained')
    # BEAN Core reviews measured strategies; its ranking is NOT proof of learning.
    try:
        from bean.optimization.selection import ImprovementOpportunity, rank_improvements
        arms=(('fixed_bruteforce',baseline_games),('untrained_neural',cold_games),
              ('trained_neural',learned_games))
        opportunities=[]
        for label,measured in arms:
            improvement=max(0.0,measured['mean_reward']-baseline_games['mean_reward'])
            opportunities.append(ImprovementOpportunity(
                identifier=label,
                description='Vaultbreaker verified replay and reward: '+label,
                evidence_refs=('vault:all-cases-replayed',f'vault:{label}:measured'),
                impact=min(5,int(improvement/2)),reproducibility=5,
                confidence=measured['win_rate'],risk=0,validation_ready=True))
        review={'provider':'bean.optimization.selection.rank_improvements',
                'ranked':[{'arm':entry.opportunity.identifier,'heuristic_score':entry.score}
                          for entry in rank_improvements(opportunities)],
                'caution':'Ranking heuristic only, not proof of neural learning.'}
    except ImportError:
        review={'provider':'unavailable_in_this_runtime','ranked':[],
                'caution':'Core not imported; do not claim Core participation.'}
    result={'schema':'bean.vault.experiment.v1','synthetic':True,'secret_space':len(CODES),
            'training_cases':training,'holdout_cases':holdout,'seed':seed,
            'neural_updates':policy.updates,'initial_weights_sha256':initial_hash,
            'saved_weights_sha256':policy.digest(),'reloaded_weights_sha256':recovered.digest(),
            'training':trained_games,'fixed_bruteforce':baseline_games,
            'untrained_neural':cold_games,'trained_neural':learned_games,'bean_core_review':review,
            'blind_holdout':'same never-trained secrets for all three arms; no weights update during evaluation',
            'causal_learning_claim':False,
            'interpretation':'Score comparisons use independent oracle; no generalized learning claim without matched advantage.'}
    (root/'report.json').write_bytes(encode(result)+b'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description='BEAN Vaultbreaker: compressed replay and neural rewards')
    parser.add_argument('--output',type=Path,default=Path('vaultbreaker-evidence'))
    parser.add_argument('--training',type=int,default=36)
    parser.add_argument('--holdout',type=int,default=18)
    args=parser.parse_args()
    result=experiment(args.output,args.training,args.holdout)
    print(json.dumps({'training':{k:result['training'][k] for k in ('win_rate','mean_turns','mean_reward')},
        'baseline':{k:result['fixed_bruteforce'][k] for k in ('win_rate','mean_turns','mean_reward')},
        'untrained':{k:result['untrained_neural'][k] for k in ('win_rate','mean_turns','mean_reward')},
        'trained':{k:result['trained_neural'][k] for k in ('win_rate','mean_turns','mean_reward')},
        'neural_updates':result['neural_updates'],
        'policy_state_persisted':result['saved_weights_sha256']==result['reloaded_weights_sha256']},indent=2))


if __name__=='__main__':
    main()
