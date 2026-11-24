"""Read-only exact-file audit for the frozen corrected experiment.

Creates separate audit output; never edits model receipts or generates artwork.
"""
from pathlib import Path
import hashlib,json,sys,tempfile
sys.path.insert(0,"/workspace/BEAN-draw-planned")
from PIL import Image,ImageChops
from bean.creativity.sketch_lab import decode,draw_svg
from bean.creativity.artifacts import file_hash,rasterize,utc_now,write_json
from bean.creativity.drawing_benchmark import summarize
from bean.learning import NativeReasoningService
root=Path('/workspace/bean-live-evidence/recent-memory-benchmark')
out=Path('/workspace/bean-live-evidence/recent-memory-benchmark-host-audit')
out.mkdir(parents=True,exist_ok=True)
if not (root/'execution.json').is_file():raise SystemExit('Run not complete; no audit conclusion emitted')
summary=summarize(root)
execution=json.loads((root/'execution.json').read_text())
results=[]
journal_payloads={}
for database in ('training','adaptive','frozen','none'):
 path=root/(database+'.sqlite3')
 core=NativeReasoningService(path)
 try:
  core.bank.journal.verify()
  journal_payloads[database]={r['entry_digest']:json.loads(r['payload'])['data'] for r in core.bank.journal.db.execute('SELECT entry_digest,payload FROM attempts')}
 finally:core.close()
with tempfile.TemporaryDirectory(prefix='bean-recent-integrity-') as temp:
 temp=Path(temp)
 for cell in execution['cells']:
  folder=root/cell['folder']/'attempts'
  run=json.loads((folder/'run.json').read_text())
  assert file_hash(folder/'model_calls.json')==run['model_calls_sha256']
  for h in run['history']:
   sidecar=folder/('attempt_%02d.json'%h['attempt']);row=json.loads(sidecar.read_text())
   assert file_hash(sidecar)==h['metadata_sha256']
   actual={**row,'schema':'bean.adaptive_lab026.v1'};actual.pop('journal_tip')
   bank='training' if cell['phase']=='training' else cell['arm']
   assert journal_payloads[bank][row['journal_tip']]==actual
   rawfile=folder/row['raw_file'];assert file_hash(rawfile)==row['raw_sha256']
   result={'phase':cell['phase'],'arm':cell['arm'],'challenge':cell['challenge'],'subject':cell['subject'],'attempt':h['attempt'],'status':row['status'],'source_git_sha':row['source_git_sha'],'sidecar_sha256':file_hash(sidecar),'svg':None,'png':None,'vision_receipt':None,'model_shapes_to_svg':None}
   if row.get('svg_file'):
    svg=folder/row['svg_file'];png=folder/row['png_file']
    assert file_hash(svg)==row['svg_sha256']==h['sha256']
    assert file_hash(png)==row['png_sha256']==h['png_sha256']
    calls=json.loads(rawfile.read_text())
    event=next(x for x in calls if x['prompt'].startswith('Draw your chosen subject, '))
    reply=event['response'];drawing=decode(reply['raw_text'] if isinstance(reply,dict) else reply)
    regenerated=temp/'actual-model-primitives.svg';draw_svg(drawing['shapes'],regenerated,'stdlib')
    assert regenerated.read_bytes()==svg.read_bytes()
    rasterize(svg,temp/'rerender.png')
    with Image.open(png) as original,Image.open(temp/'rerender.png') as rendered:
     assert original.size==rendered.size
     assert ImageChops.difference(original.convert('RGB'),rendered.convert('RGB')).getbbox() is None
    result.update(svg=row['svg_sha256'],png=row['png_sha256'],model_shapes_to_svg='exact_bytes')
    feedback=row.get('external_feedback') or {}
    if feedback.get('review_file'):
     vision=folder/feedback['review_file'];assert file_hash(vision)==feedback['review_sha256']
     result['vision_receipt']=file_hash(vision)
   results.append(result)
 journal_reports=[]
 for name in ('training','adaptive','frozen','none'):
  path=root/(name+'.sqlite3');before=file_hash(path)
  core=NativeReasoningService(path)
  try:
   core.bank.journal.verify()
   rows=list(core.bank.journal.db.execute('SELECT entry_digest,payload FROM attempts ORDER BY id'))
   journal_reports.append({'database':path.name,'sha256':before,'rows':len(rows),'last_tip':rows[-1]['entry_digest'] if rows else None,'chain':'verified'})
  finally:core.close()
  assert file_hash(path)==before
 write_json(out/'integrity.json',{'schema':'bean.draw.recent_memory.integrity.v1','observed_at_utc':utc_now(),'source_git_sha':'bb7128d76a6c210d84234326576ef6bc7f1e2509','attempts':results,'journals':journal_reports,'summary_recomputed':summary,'independently_authenticated':False,'scope':'Actual file hashes, raw-model primitives, decoded PNG pixels, linked vision receipts, Core SHA chains and delivered memory; not aesthetic correctness'})
print(json.dumps({'attempts':len(results),'svg_png_pairs':sum(bool(x['svg'] and x['png']) for x in results),'artifact_failures':[x for x in summary['outcomes'] if x.get('artifact_verification_error')],'memory_validity':summary['memory_comparison_validity'],'deltas':summary['generalization_adaptive_minus_control']},indent=2))
