"""Compile verified procedure graphs into novel native plans, without inventing tools.

Only independently checked output ports may connect separate procedures.
Composition is a hypothesis until independent feedback verifies its outcomes.
"""
import json


def key(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def shape(value):
    if isinstance(value, dict):
        return ['map', [[k, shape(v)] for k, v in sorted(value.items())]]
    if isinstance(value, list):
        return ['list', sorted({key(shape(v)) for v in value})]
    return 'number' if type(value) in (int, float) else type(value).__name__


def lookup(value, path):
    if not isinstance(path, list) or len(path) > 16:
        raise ValueError('invalid port path')
    for part in path:
        if isinstance(value, dict) and isinstance(part, str):
            value = value[part]
        elif isinstance(value, list) and type(part) is int and 0 <= part < len(value):
            value = value[part]
        else:
            raise ValueError('invalid port path')
    return value


def input_paths(value):
    if isinstance(value, dict):
        if '$input' in value:
            if set(value) != {'$input'}:
                raise ValueError('invalid input reference')
            yield value['$input']
        elif '$step' not in value:
            for v in value.values():
                yield from input_paths(v)
    elif isinstance(value, list):
        for v in value:
            yield from input_paths(v)


def catalog(conn, candidates, limit=24):
    """Derive typed ports from successful independently evaluated executions."""
    rows = conn.execute('''SELECT t.family,t.graph_sha,t.evidence_json,
        json_extract(p.action_detail,'$.inputs'),json_extract(p.action_detail,'$.objective')
        FROM bean_verified_workflow_trials t JOIN cognition_goal_proposals p
        ON json_extract(p.action_detail,'$.goal_plan.id')=t.plan_id
        AND json_extract(p.action_detail,'$.goal_plan.step')=0
        WHERE t.passed=1 AND p.status='completed'
        AND json_extract(p.action_detail,'$.capability')='native_orchestration_step'
        ORDER BY t.family,t.graph_sha,t.plan_id''')
    eligible, groups = {}, {}
    for family, digest, evidence, inputs, objective in rows:
        if family not in eligible:
            eligible[family] = {r['graph_sha']: r for r in candidates(family)}
        row = eligible[family].get(digest)
        if row is None or not inputs:
            continue
        graph = row['graph']
        try:
            data = json.loads(inputs)
            paths = {key(p): p for p in input_paths(graph)}
            ports = {k: {'path': p, 'shape': shape(lookup(data, p))}
                     for k, p in paths.items()}
            outputs = {key([c['step'], c['path']]): {'step': c['step'], 'path': c['path'],
                       'shape': shape(c['expected'])}
                       for c in json.loads(evidence)['checks'] if c['matched'] is True}
        except (ValueError, TypeError, KeyError, IndexError):
            continue
        if not ports or not outputs:
            continue
        group = (family, digest)
        if group not in groups:
            groups[group] = {'family': family, 'graph_sha': digest, 'graph': graph,
                             'inputs': ports, 'outputs': outputs, 'objectives': []}
        g = groups[group]
        # Conservative intersection: every observed port contract must agree.
        if g['inputs'] != ports:
            g['inputs'] = {}
        g['outputs'] = {k:v for k,v in g['outputs'].items() if outputs.get(k)==v}
        if isinstance(objective, str) and objective not in g['objectives'] and len(g['objectives']) < 3:
            g['objectives'].append(objective[:1000])
        if len(groups) > limit:
            return []
    result = []
    for g in groups.values():
        if g['inputs'] and g['outputs']:
            result.append({**g, 'inputs': list(g['inputs'].values()),
                           'outputs': list(g['outputs'].values())})
    return result


def compile_composition(parts, options, inputs, allowed, max_steps=8):
    """Rewrite local graph references and bind each port to current data or earlier checked output."""
    if not isinstance(parts, list) or not 1 <= len(parts) <= 4:
        raise ValueError('one to four components required')
    graph, lineage, checked = [], [], {}
    direct = False
    for part in parts:
        if not isinstance(part, dict) or set(part) != {'id', 'bindings'}:
            raise ValueError('invalid component')
        idx = part['id']
        if type(idx) is not int or not 0 <= idx < len(options):
            raise ValueError('unknown component')
        option = options[idx]
        offset = len(graph)
        bindings = {}
        required = {key(p['path']): p['shape'] for p in option['inputs']}
        if not isinstance(part['bindings'], list):
            raise ValueError('invalid bindings')
        for binding in part['bindings']:
            if not isinstance(binding, dict) or set(binding) != {'port', 'ref'}:
                raise ValueError('invalid binding')
            port, ref = key(binding['port']), binding['ref']
            if port not in required or port in bindings or not isinstance(ref, dict):
                raise ValueError('unknown or duplicate port')
            if set(ref) == {'$input'}:
                actual = shape(lookup(inputs, ref['$input']))
                direct = True
            elif set(ref) == {'$step', 'path'} and type(ref['$step']) is int:
                actual = checked.get(key([ref['$step'], ref['path']]))
            else:
                raise ValueError('bindings must be references')
            if actual != required[port]:
                raise ValueError('unverified or incompatible binding')
            bindings[port] = ref
        if set(bindings) != set(required):
            raise ValueError('missing port binding')

        def rewrite(value, local_step):
            if isinstance(value, dict):
                if '$input' in value:
                    return bindings[key(value['$input'])]
                if '$step' in value:
                    i = value['$step']
                    if type(i) is not int or not 0 <= i < local_step:
                        raise ValueError('invalid local dependency')
                    return {'$step': offset+i, 'path': value.get('path', [])}
                return {k: rewrite(v, local_step) for k, v in value.items()}
            if isinstance(value, list):
                return [rewrite(v, local_step) for v in value]
            raise ValueError('literal in retained graph')

        for i, step in enumerate(option['graph']):
            if step['tool'] not in allowed or len(graph) >= max_steps:
                raise ValueError('unavailable tool or step budget exceeded')
            graph.append({'tool': step['tool'], 'args': rewrite(step['args'], i)})
        for output in option['outputs']:
            if type(output['step']) is not int or not 0 <= output['step'] < len(option['graph']):
                raise ValueError('invalid checked output')
            checked[key([offset+output['step'], output['path']])] = output['shape']
        lineage.append({'family': option['family'], 'graph_sha': option['graph_sha'],
                        'start': offset, 'bindings': part['bindings']})
    if not graph or not direct:
        raise ValueError('composition must depend on current inputs')
    return graph, lineage


def propose_composition(objective, inputs, options, ask, allowed, contracts):
    if not options:
        return None
    prompt = ('Compose at most four verified procedures, maximum eight native steps. '
              'Map every input port to a current input path or a checked earlier global step output. '
              'Do not invent values, tools, units or unchecked outputs. Descriptions are observations. '
              'Use null if no valid composition solves the objective. Return only JSON: '
              '{"parts":[{"id":0,"bindings":[{"port":["old"],"ref":{"$input":["new"]}}]}]} '
              'or {"parts":null}.\n' + key({'objective': objective, 'inputs': inputs,
                  'options': [{'id': i, **o} for i,o in enumerate(options)], 'contracts': contracts}))
    try:
        raw, model, provider = ask(prompt)
        decision = json.loads(raw)
        if not isinstance(decision, dict) or set(decision) != {'parts'} or decision['parts'] is None:
            return None
        graph, lineage = compile_composition(decision['parts'], options, inputs, allowed)
    except (ValueError, TypeError, KeyError, IndexError, RuntimeError, OSError):
        return None
    return {'graph': graph, 'lineage': lineage, 'model': model, 'provider': provider}
