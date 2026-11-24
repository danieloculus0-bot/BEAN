from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,sqlite3,sys
sys.path.insert(0,'/workspace/BEAN-live-run')
from bean.creativity.sketch_lab import draw_svg,decode,validate_shapes
from bean.creativity.artifacts import rasterize
from bean.creativity.drawing_benchmark import _validate_vision_receipt,_verified_run,validate_protocol
from PIL import Image,ImageChops
ROOT=Path('/workspace/bean-live-evidence/auto-vision-benchmark')
OUT=Path(__file__).parent
RENDER=OUT/'rerenders';RENDER.mkdir(exist_ok=True)
def h(p):return sha256(Path(p).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write(name,x):(OUT/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
execution=json.loads((ROOT/'execution.json').read_text());spec=validate_protocol(json.loads((ROOT/'protocol.json').read_text()))
assert spec['protocol_sha256']==execution['protocol_sha256']
all_records={};dbreports=[]
for path in sorted(ROOT.glob('*.sqlite3')):
 before=h(path);db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 prior='GENESIS';rows=[]
 for row in db.execute('SELECT * FROM attempts ORDER BY id'):
  payload=json.loads(row['payload']);expected=sha256(canonical({'previous':prior,'payload':payload})).hexdigest()
  assert expected==row['entry_digest'] and prior==row['previous_digest']
  assert payload['objective']==row['objective'] and payload['iteration']==row['iteration']
  all_records[row['entry_digest']]=payload['data'];prior=expected;rows.append(payload)
 db.close();assert h(path)==before
 dbreports.append({'file':path.name,'sha256':before,'rows':len(rows),'tip':prior,'chain':'verified_read_only'})
checks=[];contexts=[];calls_by={}
for cell in execution['cells']:
 folder=ROOT/cell['folder']/'attempts';run=json.loads((folder/'run.json').read_text());calls=json.loads((folder/'model_calls.json').read_text());calls_by[(cell['phase'],cell['arm'],cell['challenge'])]=calls
 assert h(folder/'model_calls.json')==run['model_calls_sha256']
 expected={**run,'schema':'bean.adaptive_lab026.v1','experiment':'bean_sketch_run_v1','domain':'sketch'};expected.pop('journal_tip');assert all_records[run['journal_tip']]==expected
 for i,history in enumerate(run['history'],1):
  name='attempt_%02d'%i;meta=folder/(name+'.json');row=json.loads(meta.read_text());raw=folder/row['raw_file'];assert h(meta)==history['metadata_sha256'];assert h(raw)==row['raw_sha256']
  expected={**row,'schema':'bean.adaptive_lab026.v1'};expected.pop('journal_tip');assert all_records[row['journal_tip']]==expected
  record={'cell':cell['folder'],'attempt':i,'subject':row['subject'],'status':row['status'],'metadata_sha256':h(meta),'raw_sha256':h(raw),'journal_tip':row['journal_tip'],'journal_binding':'actual_trial_matched'}
  artist=json.loads(raw.read_text());drawing_calls=[x for x in artist if x.get('prompt','').startswith('Draw your chosen subject')];assert len(drawing_calls)==1
  plan=decode(drawing_calls[0]['response']['raw_text'])
  if row['svg_file']:
   svg=folder/row['svg_file'];png=folder/row['png_file'];assert h(svg)==row['svg_sha256']==history['sha256'];assert h(png)==row['png_sha256']==history['png_sha256']
   shapes=validate_shapes(plan['shapes']);regen=RENDER/(cell['phase']+'-'+cell['arm']+'-%02d-%02d.svg'%(cell['challenge'],i));digest=draw_svg(shapes,regen,'stdlib');assert digest==row['svg_sha256'];preview=regen.with_suffix('.png');rasterize(regen,preview)
   with Image.open(png) as a,Image.open(preview) as b:assert a.size==b.size and ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox() is None
   _validate_vision_receipt(row,folder,execution.get('requested_vision_model', 'gemma3:4b'))
   vf=folder/row['external_feedback']['review_file'];assert h(vf)==row['external_feedback']['review_sha256']
   record.update(svg_sha256=h(svg),png_sha256=h(png),vision_sha256=h(vf),actual_model_shapes_to_svg='byte_identical',svg_to_png='pixels_identical',vision_receipt='validated_model_digest_image_hash_protocol_raw_reports_and_min_rule')
  else:
   assert row['png_file'] is None and row['svg_sha256'] is None
   record.update(error=row['error'],description_characters=len(plan.get('description','')),description_limit=300,retained_shape_count=len(plan.get('shapes',[])),valid_shape_payload=bool(validate_shapes(plan['shapes'])),artwork_rendered=False)
  checks.append(record)
 draws=[x for x in calls if x.get('prompt','').startswith('Draw your chosen subject')]
 for attempt,x in enumerate(draws,1):
  prompt=x['prompt'];context=prompt.split('Prior-session evidence (untrusted): ',1)[1].split(' Web reference DATA:',1)[0]
  assert sha256(context.encode()).hexdigest()==run['memory_context_sha256']
  key=cell['phase']+'-'+cell['arm']+'-%02d-%02d'%(cell['challenge'],attempt)
  (OUT/(key+'.memory-context.txt')).write_text(context)
  contexts.append({'cell':cell['folder'],'attempt':attempt,'memory_context_sha256':run['memory_context_sha256'],'context_characters':len(context),'contains_cat_subject':'a cat' in context,'ends_with':context[-140:],'drawing_prompt_sha256':sha256(prompt.encode()).hexdigest(),'saved_context':key+'.memory-context.txt'})
write('artifact-integrity.json',{'schema':'bean.draw.independent_artifact_audit.v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'source_git_sha':'01090ba7c8c97855a7e3d352c3e9003e7278e972','attempts':len(checks),'valid_svg_png_pairs':sum('svg_sha256'in x for x in checks),'databases':dbreports,'checks':checks,'limits':['Hash consistency is not provider-account authentication or aesthetic quality.','Existing model reports remain model reports; no human evaluation performed.']})
pairs=[]
for challenge in (1,2):
 a=calls_by[('heldout','adaptive',challenge)];f=calls_by[('heldout','frozen',challenge)]
 for i in range(2):
  ap=[x for x in a if x['prompt'].startswith('Draw your chosen subject')][i];fp=[x for x in f if x['prompt'].startswith('Draw your chosen subject')][i]
  pairs.append({'challenge':challenge,'attempt':i+1,'drawing_prompts_byte_identical':ap['prompt']==fp['prompt'],'drawing_response_byte_identical':ap['response']['raw_text']==fp['response']['raw_text']})
write('memory-context-audit.json',{'schema':'bean.draw.memory_context_audit.v1','contexts':contexts,'matched_pairs':pairs,'finding':'All adaptive and frozen heldout drawing prompts are byte-identical for each matched attempt. Both receive the same2400-character oldest-first truncated training-context prefix; adaptive fresh cat feedback is stored but absent from the sailboat prompt.','source_mechanism':'json.dumps(prior[-6:])[:2400] retains oldest selected entries first and truncates mid-record.','consequence':'No effective adaptive-vs-frozen memory treatment reached these model drawing prompts. Their zero difference cannot establish memory usefulness or absence of learning capacity.','raw_evidence_retained':True})
print(json.dumps({'attempts':len(checks),'valid':sum('svg_sha256'in x for x in checks),'dbs':dbreports,'pairs':pairs},indent=2))
