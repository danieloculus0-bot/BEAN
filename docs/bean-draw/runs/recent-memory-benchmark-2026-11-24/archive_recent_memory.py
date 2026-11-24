"""Copy only the completed public drawing experiment and hash every byte.

This is an archive/verification helper, not an artist and never calls a model.
"""
from pathlib import Path
import datetime,gzip,hashlib,json,re,shutil,sqlite3,subprocess,sys,tempfile
sys.path.insert(0,'/workspace/BEAN-draw-planned')
from bean.creativity.drawing_benchmark import summarize
from bean.learning import NativeReasoningService

ROOT=Path('/workspace/bean-live-evidence')
SOURCE=ROOT/'recent-memory-benchmark'
DEST=Path('/workspace/BEAN/docs/bean-draw/runs/recent-memory-benchmark-2026-11-24')
SHA='bb7128d76a6c210d84234326576ef6bc7f1e2509'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def normalized(x):return json.loads(json.dumps(x))
copies=[]
def copy(src,rel):
 dst=DEST/rel;dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert dst.read_bytes()==src.read_bytes(),str(dst)
 else:shutil.copyfile(src,dst)
 assert src.read_bytes()==dst.read_bytes()
 copies.append({'source_file':str(src.relative_to(ROOT)),'archive_file':str(rel),'bytes':src.stat().st_size,'sha256':digest(src)})
assert (SOURCE/'execution.json').is_file()
summary=json.loads((SOURCE/'summary.json').read_text())
assert normalized(summarize(SOURCE))==summary
DEST.mkdir(parents=True,exist_ok=True)
for src in sorted(SOURCE.rglob('*')):
 if src.is_file() and not any(src.name.endswith(s) for s in ('.sqlite3','.sqlite3-wal','.sqlite3-shm')):
  copy(src,Path('original')/src.relative_to(SOURCE))
for name in ['recent-memory-benchmark-protocol.json','recent-memory-benchmark-preregistration.json','recent-memory-benchmark.stdout.json','recent-memory-benchmark.stderr.log','audit_recent_memory_run.py','archive_recent_memory.py','write_recent_visual_audit.py']:
 copy(ROOT/name,Path(name))
copy(ROOT/'recent-memory-benchmark-host-audit/integrity.json',Path('audit/integrity.json'))
copy(ROOT/'recent-memory-benchmark-host-audit/final-visual-review.json',Path('audit/final-visual-review.json'))
for src in sorted((ROOT/'recent-memory-benchmark-host-audit/images').glob('*.json')):
 copy(src,Path('audit/earlier-host-observations')/src.name)
journals=[]
with tempfile.TemporaryDirectory(prefix='bean-recent-archive-') as temporary:
 for name in ['training','adaptive','frozen','none']:
  src=SOURCE/(name+'.sqlite3');before=digest(src);dst=Path(temporary)/(name+'.sqlite3')
  source=sqlite3.connect(src.as_uri()+'?mode=ro',uri=True);target=sqlite3.connect(dst)
  source.backup(target)
  tables=[r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  counts={}
  for table in tables:
   assert re.fullmatch('[a-z_]+',table)
   a=source.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
   b=target.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
   assert a==b;counts[table]=len(a)
  rows=source.execute('SELECT entry_digest FROM attempts ORDER BY id').fetchall()
  source.close();target.close()
  raw_sha=digest(dst);core=NativeReasoningService(dst)
  try:core.bank.journal.verify()
  finally:core.close()
  assert digest(dst)==raw_sha
  gz=DEST/'journals'/(name+'.sqlite3.gz');gz.parent.mkdir(parents=True,exist_ok=True)
  data=gzip.compress(dst.read_bytes(),mtime=0)
  if gz.exists():assert gz.read_bytes()==data
  else:gz.write_bytes(data)
  assert gzip.decompress(gz.read_bytes())==dst.read_bytes()
  assert digest(src)==before
  journals.append({'source_file':src.name,'archive_file':str(gz.relative_to(DEST)),'source_sha256_before_reverification':before,'source_sha256_after_reverification':digest(src),'source_bytes':src.stat().st_size,'raw_backup_sha256':raw_sha,'raw_backup_bytes':dst.stat().st_size,'compressed_sha256':digest(gz),'compressed_bytes':gz.stat().st_size,'gzip_mtime':0,'online_backup_created':True,'chain_verified':True,'source_and_backup_rows_identical':True,'table_row_counts':counts,'rows':len(rows),'tip':rows[-1][0] if rows else None})
execution=json.loads((SOURCE/'execution.json').read_text());attempts=[];runtime=[]
for cell in execution['cells']:
 folder=SOURCE/cell['folder']/'attempts';run=json.loads((folder/'run.json').read_text())
 assert run['execution_mode']=='live_model' and run['source_git_sha']==SHA
 for filename,expected in run['runtime_source_sha256'].items():
  blob=subprocess.check_output(['git','show',SHA+':'+filename],cwd='/workspace/BEAN')
  assert hashlib.sha256(blob).hexdigest()==expected
  assert hashlib.sha256((Path('/workspace/BEAN-draw-planned')/filename).read_bytes()).hexdigest()==expected
 runtime.append({'folder':cell['folder'],'source_git_sha':SHA,'runtime_source_sha256':run['runtime_source_sha256'],'recorded_modules_match_git_blobs':True})
 for h in run['history']:
  row=json.loads((folder/('attempt_%02d.json'%h['attempt'])).read_text())
  attempts.append({k:row.get(k) for k in ['subject','subject_source','attempt','status','error','source_git_sha','svg_file','png_file']})
write(DEST/'audit/runtime-source-verification.json',{'source_git_sha':SHA,'scope':'recorded runtime module hashes match pinned Git blobs and unchanged execution worktree; not provider authentication','runs':runtime})
write(DEST/'source-copy-manifest.json',{'schema':'bean.draw.archive.sources.v1','archived_at_utc':stamp(),'source_root':str(SOURCE),'source_git_sha':SHA,'original_summary_reproduced_from_frozen_source':True,'source_databases_unchanged':True,'original_and_audit_copies':copies,'journals':journals,'attempts':attempts,'weights_updated':False,'learning_improvement_verified':False,'retained_learning_contrast_valid':True,'eligible_adaptive_frozen_contrasts':1,'model_ratings_not_ground_truth':True})
print(json.dumps({'archived_files_so_far':sum(p.is_file() for p in DEST.rglob('*')),'copied_source_files':len(copies),'journals':[{k:x[k] for k in ['source_file','rows','chain_verified','source_and_backup_rows_identical']} for x in journals],'svg_png_pairs':sum(bool(x['svg_file'] and x['png_file']) for x in attempts),'source':SHA},indent=2))
