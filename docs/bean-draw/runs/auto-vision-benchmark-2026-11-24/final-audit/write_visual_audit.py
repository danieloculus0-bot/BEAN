"""Persist observations only after all nine view_image results were inspected."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json

root=Path('/workspace/bean-live-evidence/auto-vision-benchmark')
out=Path('/workspace/bean-live-evidence/auto-vision-benchmark-final-audit')
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
def write(p,data):Path(p).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
# These are posthoc observations made after actual image-display tool results.
observations={
'29ff58275ec51c5f9c2ea6c5cd00b4eee1516ec35ab89bc38c3eebd3d6128d54':('A thin band of angular outlines, two circles and short strokes occupies the top edge; most of the canvas is blank. I cannot identify a coherent cat.',1),
'00a049c302c8bc4a2d4f8c08c86113812306b13199aff98bf66871eafe83a0a9':('A small cluster of overlapping circles sits across several short horizontal/diagonal strokes near the upper-left of center. No legible cat outline or connected animal form is visible to me.',1),
'8dcbf8949e70da5fafe931a3f77571c51a71483af7b8aa6a94211916c3612b58':('An outlined rectangle is crossed by diagonals; an angular zigzag sits above it, a large circle is clipped at the left edge, and a small lower circle and detached bottom line remain. These marks do not form a reliably recognizable sailboat to me.',1),
'6b0639d85888552add0bf98df37758cadc517c1ae76dda77cf0946b8db74ef77':('A large rectangular frame, long horizontal lines, two overlapping upper-left circles and several downward diagonal strokes are visible. I cannot identify a coherent sailboat from the connected arrangement.',1),
'2dc974433a505c7c293d72d7beacf6a55364541b6251cebafffec0158cceef69':('One larger circle and several overlapping smaller circles form a dense right-of-center cluster, crossed by diagonal and short horizontal lines. I cannot recognize a cat in the cluster.',1),
'8d9ad786996d0403eb7c806229d49ca7c0916f454a8751f6e277ba75517a1ba8':('A repeated row of overlapping circles makes a clear middle band with a baseline; additional larger circles overlap below and at the clipped right edge. The repeated band offers some compositional order, but I cannot recognize a cat.',2),
'b37201dd986de1abf0fd207656c516c1eb5264adf5dd4aaabbe1891e7d3511ae':('A long rising diagonal crosses a vertical line; a circle and small right-angle strokes occupy the lower-right area. The components do not form a reliably recognizable sailboat to me.',1),
'3c421e7071e42db86827d41370646c2d617d3a09ae0a921f6e95b120c9b912df':('Two long vertical lines, circles at their upper ends, a low horizontal baseline, several lower circle clusters and an isolated left circle are visible. I cannot recognize a connected teapot vessel, handle and spout.',1),
'6e4235ea96ab45e6b7d2aaf7e709340c2e4e788fabdc3b4cabecb8ce4a5e7a1b':('One long rising diagonal and a small cluster of three circles beside a short horizontal line dominate the image. No coherent teapot is recognizable to me; the apparent simplification does not establish better depiction.',1),
}
unique={}
for p in sorted(root.glob('**/attempt_[0-9][0-9].json')):
 row=json.loads(p.read_text())
 if row.get('png_file'):
  info=unique.setdefault(row['png_sha256'],{'path':p.parent/row['png_file'],'subject':row['subject'],'cells':[]})
  assert info['subject']==row['subject']
  info['cells'].append(str(p.relative_to(root)))
reports=[]
for h,info in unique.items():
 assert digest(info['path'])==h
 text,composition=observations[h]
 report={'schema':'bean.draw.final_host_visual_audit.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'kind':'vision_model','evaluator':'Codex final-experiment visual audit agent',
 'model_identity_limit':'Exact host assistant model digest is not exposed by the image inspection tool',
 'subject':info['subject'],'image_sha256':h,'image_file':str(info['path'].relative_to(root)),
 'attempt_receipts':info['cells'],'feedback':text,
 'scores':{'spatial_coherence':1,'subject_recognition':0,'composition':composition},
 'satisfactory':False,'blinded':False,'posthoc':True,'used_for_generation':False,
 'inspection_method':'Actual PNG opened with view_image; report written in a separate later tool call after displayed pixels were inspected',
 'human_evaluation':None,'independently_authenticated':False}
 path=out/'visual'/(h+'.json');write(path,report);reports.append({'report':str(path.relative_to(out)),'sha256':digest(path),**report})
execution=json.loads((root/'execution.json').read_text());by_hash={r['image_sha256']:r for r in reports};cells=[]
for cell in execution['cells']:
 folder=root/cell['folder']/'attempts';attempts=[]
 for p in sorted(folder.glob('attempt_[0-9][0-9].json')):
  row=json.loads(p.read_text());host=by_hash.get(row.get('png_sha256'))
  attempts.append({'attempt':row['attempt'],'status':row['status'],'image_sha256':row.get('png_sha256'),
   'host_scores':host['scores'] if host else None,'automatic_scores':row.get('external_feedback',{}).get('scores'),
   'host_report':('visual/'+row['png_sha256']+'.json') if host else None})
 first,last=attempts[0]['host_scores'],attempts[-1]['host_scores']
 cells.append({k:cell[k] for k in ('phase','arm','challenge','subject')}|{'attempts':attempts,
  'host_last_minus_first':{metric:(last[metric]-first[metric] if first and last else None) for metric in ('spatial_coherence','subject_recognition','composition')}})
prior=Path('/workspace/bean-live-evidence/auto-vision-benchmark-host-audit/images')
invalid=prior/'6e4235ea96ab45e6b7d2aaf7e709340c2e4e788fabdc3b4cabecb8ce4a5e7a1b.json'
correction=prior/'6e4235ea96ab45e6b7d2aaf7e709340c2e4e788fabdc3b4cabecb8ce4a5e7a1b.correction.json'
summary={'schema':'bean.draw.final_experiment_audit.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'source_git_sha':'01090ba7c8c97855a7e3d352c3e9003e7278e972','original_execution_sha256':digest(root/'execution.json'),
 'original_summary_sha256':digest(root/'summary.json'),'original_receipts_modified':False,
 'unique_actual_pngs_inspected':len(reports),'valid_svg_png_attempts':13,'retained_failed_attempts':1,
 'subject_recognition_observed':'No reliable teapot, cat or sailboat identification in these inspected outputs',
 'visual_model_rating_disagreement':'Gemma sometimes rates recognition/coherence highly despite the final host visual observer being unable to identify the requested subject; model ratings are not independently verified artistic quality',
 'retained_learning_assessment':'INVALID adaptive-versus-frozen exposure comparison: effective memory inputs are identical because newer trial feedback was truncated from the prompt; retained-learning benefit remains UNPROVEN, not an evidenced memory tie or absence of benefit',
 'memory_failure_evidence':'integrity/context-truncation-detail.json','artifact_integrity':'integrity/artifact-integrity.json','memory_context_audit':'integrity/memory-context-audit.json',
 'automated_summary_must_not_be_used_as_learning_proof':True,
 'prior_invalidated_host_note':{'file':str(invalid),'sha256':digest(invalid),'status':'invalidated_observation_not_used_for_generation',
 'correction_file':str(correction),'correction_sha256':digest(correction),'correction_verified_against_current_actual_image':True},
 'reports':[{k:r[k] for k in ('report','sha256','image_sha256','subject','scores')} for r in reports],
 'cells':cells,'portfolio_diversity_posthoc':{
  'adaptive':{'score':1,'image_sha256s':['00a049c302c8bc4a2d4f8c08c86113812306b13199aff98bf66871eafe83a0a9','6b0639d85888552add0bf98df37758cadc517c1ae76dda77cf0946b8db74ef77'],'feedback':'Final images differ in layout and density but share circles/lines and do not reliably distinguish the two requested subjects.'},
  'frozen':{'score':1,'image_sha256s':['00a049c302c8bc4a2d4f8c08c86113812306b13199aff98bf66871eafe83a0a9','6b0639d85888552add0bf98df37758cadc517c1ae76dda77cf0946b8db74ef77'],'feedback':'Same inspected final images as adaptive.'},
  'none':None},
 'limitations':['Unblinded subjective host-model observation; no human evaluation or authenticated ground truth.',
 'A minor composition-rating increase in one no-memory cat revision does not establish recognition or learning.',
 'Failed no-memory sailboat final attempt prevents a complete matched final comparison for that case.',
 'Original null/automatic model reports remain preserved, not rewritten with these posthoc scores.'],
 'weights_updated':False,'learning_improvement_verified':False,'independent_evaluation_authenticated':False}
write(out/'final-host-audit-summary.json',summary)
files={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file() and p.name not in ('audit-manifest.json',)}
write(out/'audit-manifest.json',{'schema':'bean.draw.audit.files.v1','files':files})
print(out/'final-host-audit-summary.json')
