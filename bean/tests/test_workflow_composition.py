import json
import math
import random
import sqlite3
import unittest

from bean.runtime.workflow_composition import catalog, compile_composition, propose_composition, shape


def inp(path):
    return {'$input': path}


def out(step, path):
    return {'$step': step, 'path': path}


def bind(port, ref):
    return {'port': [port], 'ref': ref}


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('''CREATE TABLE bean_verified_workflow_trials
            (family TEXT,plan_id TEXT,graph_sha TEXT,evidence_json TEXT,passed INTEGER);
            CREATE TABLE cognition_goal_proposals (action_detail TEXT,status TEXT);''')
        self.verified = {}
        self.add('orbit', [{'tool':'orbit_reference','args':{'altitude_km':inp(['h'])}}],
                 {'h':200}, [{'step':0,'path':['speed'],'expected':7.8,'matched':True}])
        self.add('acceleration', [{'tool':'acceleration_reference','args':{'speed':inp(['v']),'rate':inp(['a'])}}],
                 {'v':8,'a':2}, [{'step':0,'path':['time'],'expected':4000,'matched':True}])
        self.options = catalog(self.db, lambda f: self.verified[f])
        self.ids = {o['family']:i for i,o in enumerate(self.options)}
        self.parts = [{'id':self.ids['orbit'],'bindings':[bind('h',inp(['mission','altitude']))]},
                      {'id':self.ids['acceleration'],'bindings':[bind('v',out(0,['speed'])),bind('a',inp(['engine','rate']))]}]
        self.inputs = {'mission':{'altitude':400},'engine':{'rate':5}}
        self.allowed = {'orbit_reference','acceleration_reference'}

    def tearDown(self):
        self.db.close()

    def add(self, family, graph, inputs, checks):
        self.verified[family] = [{'graph_sha':family,'graph':graph}]
        for i in range(2):
            pid = family+str(i)
            self.db.execute('INSERT INTO bean_verified_workflow_trials VALUES (?,?,?,?,1)',
                (family,pid,family,json.dumps({'checks':checks})))
            self.db.execute('INSERT INTO cognition_goal_proposals VALUES (?,?)',
                (json.dumps({'goal_plan':{'id':pid,'step':0},'inputs':inputs,'objective':family,
                             'capability':'native_orchestration_step'}),'completed'))

    def compile(self, parts=None, inputs=None, allowed=None, **kwargs):
        return compile_composition(self.parts if parts is None else parts,self.options,
            self.inputs if inputs is None else inputs,self.allowed if allowed is None else allowed,**kwargs)

    def test_novel_schema_and_composed_execution_on_100_cases(self):
        rng = random.Random(527)
        for _ in range(100):
            h, a = rng.uniform(150,1800),rng.uniform(.2,15)
            data={'mission':{'altitude':h},'engine':{'rate':a}}
            graph,lineage=self.compile(inputs=data)
            self.assertEqual(graph[0]['args']['altitude_km'],inp(['mission','altitude']))
            self.assertEqual(graph[1]['args']['speed'],out(0,['speed']))
            outputs=[]
            def resolve(ref):
                value=data if '$input' in ref else outputs[ref['$step']]
                for p in ref.get('$input',ref.get('path',[])):
                    value=value[p]
                return value
            for step in graph:
                args={k:resolve(v) for k,v in step['args'].items()}
                if step['tool']=='orbit_reference':
                    outputs.append({'speed':math.sqrt(398600.435507/(6371.0084+args['altitude_km']))})
                else:
                    outputs.append({'time':1000*args['speed']/args['rate']})
            expected=math.sqrt(398600.435507/(6371.0084+h))*1000/a
            self.assertAlmostEqual(outputs[-1]['time'],expected,places=9)
            self.assertEqual([p['family'] for p in lineage],['orbit','acceleration'])

    def test_missing_duplicate_and_literal_bindings_rejected(self):
        for bad in ([],[bind('h',inp(['mission','altitude']))]*2,[bind('h',400)]):
            with self.assertRaises(ValueError):
                self.compile(parts=[{'id':self.ids['orbit'],'bindings':bad}])

    def test_unchecked_or_future_outputs_rejected(self):
        for ref in (out(0,['unknown']),out(1,['time']),out(-1,['speed'])):
            parts=[self.parts[0],{'id':self.ids['acceleration'],'bindings':[bind('v',ref),bind('a',inp(['engine','rate']))]}]
            with self.assertRaises(ValueError):self.compile(parts=parts)

    def test_wrong_type_and_unavailable_tool_rejected(self):
        with self.assertRaises(ValueError):self.compile(inputs={'mission':{'altitude':True},'engine':{'rate':5}})
        with self.assertRaises(ValueError):self.compile(allowed={'orbit_reference'})
        with self.assertRaises(ValueError):self.compile(max_steps=1)

    def test_internal_dependencies_are_rebased(self):
        self.add('two', [{'tool':'orbit_reference','args':{'altitude_km':inp(['h'])}},
                         {'tool':'acceleration_reference','args':{'speed':out(0,['speed']),'rate':inp(['a'])}}],
                 {'h':200,'a':2},[{'step':1,'path':['time'],'expected':2,'matched':True}])
        options=catalog(self.db,lambda f:self.verified[f]); ids={o['family']:i for i,o in enumerate(options)}
        parts=[{'id':ids['orbit'],'bindings':[bind('h',inp(['mission','altitude']))]},
               {'id':ids['two'],'bindings':[bind('h',inp(['mission','altitude'])),bind('a',inp(['engine','rate']))]}]
        graph,_=compile_composition(parts,options,self.inputs,self.allowed)
        self.assertEqual(graph[2]['args']['speed'],out(1,['speed']))

    def test_catalog_excludes_revoked_and_unchecked_ports(self):
        self.verified['orbit']=[]
        options=catalog(self.db,lambda f:self.verified[f])
        self.assertEqual([o['family'] for o in options],['acceleration'])
        self.assertEqual(options[0]['outputs'],[{'step':0,'path':['time'],'shape':shape(4000)}])

    def test_model_proposal_is_not_verification(self):
        result=propose_composition('New objective',self.inputs,self.options,
            lambda p:(json.dumps({'parts':self.parts}),'fixture','local'),self.allowed,{})
        self.assertEqual(len(result['graph']),2)
        self.assertNotIn('verified',result)
        for response in ('bad','{"parts":null}','{"parts":[{"id":true,"bindings":[]}]}'):
            self.assertIsNone(propose_composition('New objective',self.inputs,self.options,
                lambda p:(response,'fixture','local'),self.allowed,{}))


if __name__=='__main__':unittest.main()
