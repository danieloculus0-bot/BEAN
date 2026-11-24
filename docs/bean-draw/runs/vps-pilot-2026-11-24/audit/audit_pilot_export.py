"""Read-only audit of exported VPS model drawings. Never contacts a provider."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,tempfile
sys.path.insert(0,'/workspace/BEAN-draw-planned')
from bean.creativity.sketch_lab import decode,draw_svg
from bean.creativity.artifacts import rasterize
from PIL import Image,ImageChops

ROOT=Path('/workspace/bean-contabo-private/download/pilot-export')
OUT=Path('/workspace/bean-contabo-private/pilot-local-audit')
REPO=Path('/workspace/BEAN-contabo-draw')
SHA='54b0a4d2c17face7ffbf3d016ef348c5a055164a'
OUT.mkdir(parents=True,exist_ok=True)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
export=json.loads((ROOT/'export-hashes.json').read_text())
for name,expected in export.items():
 p=ROOT/name;assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT.resolve())
 assert h(p)==expected,(name,h(p),expected)
assert set(export)=={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='export-hashes.json'}
folder=ROOT/'artifacts';run=json.loads((folder/'run.json').read_text())
assert run['execution_mode']=='live_model' and run['source_git_sha']==SHA
assert run['model_id']=='qwen2.5:7b' and run['subject_source']=='autonomous'
assert run['memory_context_records']==[]
assert h(folder/'model_calls.json')==run['model_calls_sha256']
modules=[]
for name,expected in run['runtime_source_sha256'].items():
 blob=subprocess.check_output(['git','show',SHA+':'+name],cwd=REPO)
 assert hashlib.sha256(blob).hexdigest()==expected,name
 assert h(Path('/workspace/BEAN-draw-planned')/name)==expected,name
 modules.append({'path':name,'sha256':expected,'matches_pinned_git_blob':True,'matches_local_replay_module':True})
calls=json.loads((folder/'model_calls.json').read_text())
choice=next(x for x in calls if x['prompt'].startswith('Choose ANY subject to draw'))
assert run['subject'] in choice['response']['raw_text']
attempts=[]
with tempfile.TemporaryDirectory(prefix='bean-vps-pilot-rerender-') as temp:
 temp=Path(temp)
 for history in run['history']:
  number=history['attempt'];sidecar=folder/('attempt_%02d.json'%number)
  row=json.loads(sidecar.read_text())
  assert h(sidecar)==history['metadata_sha256']
  assert row['subject']==run['subject'] and row['model_digest']==run['model_digest']
  assert row['journal_tip']==history['journal_tip']
  raw=folder/row['raw_file'];svg=folder/row['svg_file'];png=folder/row['png_file']
  assert h(raw)==row['raw_sha256']
  assert h(svg)==row['svg_sha256']==history['sha256']
  assert h(png)==row['png_sha256']==history['png_sha256']
  attempt_calls=json.loads(raw.read_text())
  assert all(c in calls for c in attempt_calls)
  event=next(x for x in attempt_calls if x['prompt'].startswith('Draw your chosen subject, '))
  drawing=decode(event['response']['raw_text'])
  replay_svg=temp/('attempt_%02d.svg'%number);draw_svg(drawing['shapes'],replay_svg,'stdlib')
  assert replay_svg.read_bytes()==svg.read_bytes(),('model_svg_mismatch',number)
  replay_png=temp/('attempt_%02d.png'%number);rasterize(svg,replay_png)
  with Image.open(png) as actual,Image.open(replay_png) as replay:
   assert actual.size==replay.size,(number,actual.size,replay.size)
   pixel_bbox=ImageChops.difference(actual.convert('RGB'),replay.convert('RGB')).getbbox()
   assert pixel_bbox is None,('actual_pixel_mismatch',number,pixel_bbox)
  feedback=row['external_feedback'];vision=folder/feedback['review_file']
  assert h(vision)==feedback['review_sha256']
  report=json.loads(vision.read_text())
  assert report['image_sha256']==row['png_sha256']
  assert report['report']['image_sha256']==row['png_sha256']
  assert report['subject']==row['subject']
  assert report['model_id']==feedback['model_id']
  assert report['model_digest']==feedback['model_digest']
  attempts.append({'attempt':number,'subject':row['subject'],'source_git_sha':row['source_git_sha'],'sidecar_sha256':h(sidecar),'raw_sha256':h(raw),'svg_sha256':h(svg),'png_sha256':h(png),'vision_receipt_sha256':h(vision),'raw_calls_present_in_model_calls':True,'model_shapes_to_svg':'exact_bytes','local_png_rerender':'identical_RGB_pixels','recorded_journal_tip':row['journal_tip'],'journal_payload_match':'unavailable_without_exported_journal','model_reported_scores':feedback['scores']})
first=json.loads((folder/'attempt_01.json').read_text())['external_feedback']
second=json.loads((folder/'attempt_02.raw.json').read_text())
delivery=[]
for prefix in ('Plan an original line drawing','Draw your chosen subject, '):
 event=next(x for x in second if x['prompt'].startswith(prefix))
 assert first['feedback'] in event['prompt']
 assert first['image_sha256'] in event['prompt']
 delivery.append({'prompt_kind':prefix,'prompt_sha256':hashlib.sha256(event['prompt'].encode()).hexdigest(),'attempt_1_feedback_delivered':True,'attempt_1_image_hash_delivered':True})
provider=json.loads((ROOT/'provider-integrity.json').read_text())
assert len(provider['blobs'])==13
assert all(k=='sha256:'+v['sha256'] and v['bytes']>0 for k,v in provider['blobs'].items())
missing=json.loads((ROOT/'journal-not-exported.json').read_text())
assert missing['state']=='omitted'
result={'schema':'bean.draw.vps_pilot.local_audit.v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'source_git_sha':SHA,'scope':'exported-file hashes, raw-model replay, local PNG pixels, linked vision receipts, source modules and feedback delivery; no remote connection, provider authentication or artwork-quality judgment','independently_authenticated':False,'export_hashes_verified':len(export),'export_hashes_sha256':h(ROOT/'export-hashes.json'),'source_modules':modules,'attempts':attempts,'attempt_2_feedback_delivery':delivery,'provider_integrity_receipt':{'sha256':h(ROOT/'provider-integrity.json'),'blob_records':len(provider['blobs']),'internally_consistent':True,'raw_model_blobs_locally_available_for_independent_rehash':False},'journal_verification':{'state':'unavailable','omission_receipt_sha256':h(ROOT/'journal-not-exported.json'),'reason':missing['reason'],'payload_matching_verified':False,'sha_chain_verified':False},'weights_updated':False,'learning_improvement_verified':False,'core_orchestrator_patch_live_verified':False}
write(OUT/'artifact-integrity.json',result)
print(json.dumps({'attempts':len(attempts),'export_hashes_verified':len(export),'model_svg_replay':'exact_bytes','png_rerender':'identical_RGB_pixels','runtime_modules':len(modules),'feedback_delivery':delivery,'journal_verification':result['journal_verification']},indent=2))
