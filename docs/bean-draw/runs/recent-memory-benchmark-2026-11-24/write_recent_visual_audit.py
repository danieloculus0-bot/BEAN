"""Posthoc observations of PNGs already displayed to the host reviewer.

This records review only; it never generates geometry or alters run receipts.
"""
from pathlib import Path
import hashlib, json
from datetime import datetime, timezone

root = Path('/workspace/bean-live-evidence/recent-memory-benchmark')
out = Path('/workspace/bean-live-evidence/recent-memory-benchmark-host-audit')
observations = {
 ('training','adaptive',1,1): ('An outlined rectangle intersects a large circle and long straight strokes. I cannot recognize a teapot silhouette, spout or handle.', 0, 2),
 ('training','adaptive',1,2): ('The rectangle/circle assembly remains, with a changed lower line. No recognizable teapot or recognition improvement is visible.', 0, 2),
 ('heldout','adaptive',1,1): ('A band of outlined circles, including overlapping circles, sits between long horizontal lines. I cannot identify a canopy and handle as an umbrella.', 0, 2),
 ('heldout','adaptive',1,2): ('A single outlined circle rests on a long horizontal line. Simplification is visible, but I cannot recognize an umbrella.', 0, 2),
 ('heldout','frozen',1,1): ('The same circle band and horizontal strokes as adaptive attempt 1 are visible. It is not a recognizable umbrella to this observer.', 0, 2),
 ('heldout','frozen',1,2): ('The same circle on a horizontal line as adaptive attempt 2 is visible. No umbrella recognition improvement is apparent.', 0, 2),
 ('heldout','none',1,1): ('Short disconnected diagonal strokes cluster in the upper left beneath a longer slanted line. No coherent umbrella is recognizable.', 0, 1),
 ('heldout','none',1,2): ('Circles of several sizes overlap a rectangle and long horizontal/vertical lines. No coherent canopy/handle silhouette is recognizable.', 0, 2),
 ('heldout','adaptive',2,1): ('Two large overlapping circles clipped at the bottom, long vertical strokes and a narrow rectangle are visible. The two circles weakly suggest wheels with the bicycle title supplied, but a coherent bicycle frame is absent.', 1, 2),
 ('heldout','adaptive',2,2): ('A large rectangle surrounds a horizontal band of small and large circles. I cannot recognize a bicycle frame or wheel arrangement; recognition did not improve from the weak wheel cue in attempt 1.', 0, 2),
 ('heldout','frozen',2,1): ('A long diagonal crosses horizontal lines and small circles near the edges; some shapes are clipped. I cannot recognize a bicycle.', 0, 2),
 ('heldout','frozen',2,2): ('Small circles sit at different heights around horizontal strokes and a central rectangle. I cannot recognize a coherent bicycle.', 0, 2),
 ('heldout','none',2,1): ('Large diagonals cross an almost full-canvas border, with two small side circles and rectangles. I cannot recognize a bicycle.', 0, 1),
 ('heldout','none',2,2): ('Tall vertical strokes, a narrow rectangle and circles at several heights are visible. No coherent bicycle frame and wheels are recognizable.', 0, 2),
}
execution = json.loads((root/'execution.json').read_text())
results = []
for cell in execution['cells']:
 for attempt in (1,2):
  key=(cell['phase'],cell['arm'],cell['challenge'],attempt)
  note,recognition,composition=observations[key]
  path=root/cell['folder']/'attempts'/f'attempt_{attempt:02d}.png'
  results.append({'phase':key[0],'arm':key[1],'challenge':key[2], 'subject':cell['subject'], 'attempt':attempt,
   'image_file':str(path.relative_to(root)), 'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'scores':{'spatial_coherence':1,'subject_recognition':recognition,'composition':composition}, 'observations':note})
report={'schema':'bean.draw.host_image_audit.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'evaluator':'Codex host visual observer','kind':'vision_model','independently_authenticated':False,
 'inspection_method':'All 14 individual PNGs displayed through view_image before writing this report',
 'blinded':False,'posthoc':True,'used_for_generation':False,'human_evaluation':'unavailable',
 'scale':{'minimum':0,'maximum':4},'attempts':results,
 'portfolio_review':{'bound_png_sha256':[x['image_sha256'] for x in results], 'diversity':2,
  'observations':'Several geometric arrangements differ, but all use black outlines and repeated circles/rectangles/long lines. Different files do not establish subject diversity or generalization.'},
 'conclusion':'Saved feedback delivery is verified separately. This observer found no final recognizable teapot, umbrella or bicycle, and no recognition advantage for adaptive memory over either control. Gemma ratings overstate recognition on these images. One eligible adaptive/frozen challenge cannot establish a learning effect.',
 'weights_updated':False,'learning_improvement_verified':False}
out.mkdir(parents=True,exist_ok=True)
target=out/'final-visual-review.json'
if target.exists(): raise SystemExit('Refusing to overwrite a prior review')
target.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(target)
