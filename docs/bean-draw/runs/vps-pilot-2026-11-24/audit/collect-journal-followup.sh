set -euo pipefail
umask 027
systemctl is-active --quiet bean-core.service
cd /opt/bean/drawing-src
test "$(runuser -u bean -- git rev-parse HEAD)" = 54b0a4d2c17face7ffbf3d016ef348c5a055164a
runuser -u bean -- /opt/bean/draw-venv/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,sqlite3,tarfile
from bean.learning import NativeReasoningService
from bean.creativity.sketch_lab import drawing_memory_context
data=Path('/var/lib/bean/drawing')
source=data/'art_history.sqlite3'
run_bytes=(data/'runs/20261124-vps-pilot/run.json').read_bytes()
assert hashlib.sha256(run_bytes).hexdigest()=='474dffca7552e9921be6bea177852ca908d3118b1d18f6bcbdcc4e5ce01195f0'
run=json.loads(run_bytes)
assert run['run_id']=='797a888c-4a33-4384-abcf-02ff43b11e4b'
out=data/'pilot-journal-followup-20261124'
out.mkdir(exist_ok=False)
before=hashlib.sha256(source.read_bytes()).hexdigest()
backup=out/'drawing-journal.sqlite3'
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as src,sqlite3.connect(backup) as dst:
    src.backup(dst)
core=NativeReasoningService(backup)
try:
    core.bank.journal.verify()
    events=list(core.bank.journal.events())
    assert all(e['kind']=='trial' and e['data'].get('task_ref')=='contabo-pilot-20261124' and e['data'].get('run_id')==run['run_id'] and e['data'].get('experiment') in ('bean_sketch_v1','bean_sketch_run_v1') for e in events),'Refusing unrelated journal export'
    drafts=[e['data'] for e in events if e['data']['experiment']=='bean_sketch_v1']
    finishes=[e['data'] for e in events if e['data']['experiment']=='bean_sketch_run_v1']
    assert len(drafts)==len(run['history'])==2 and len(finishes)==1 and len(events)==3
    context=drawing_memory_context(drafts)
    metadata=[{'kind':e['kind'],'experiment':e['data']['experiment'],'task_ref':e['data']['task_ref'],'run_id':e['data']['run_id'],'attempt':e['data'].get('attempt')} for e in events]
finally:core.close()
after=hashlib.sha256(source.read_bytes()).hexdigest();assert after==before
with backup.open('rb') as stream, (out/'drawing-journal.sqlite3.gz').open('wb') as target:
    with gzip.GzipFile(fileobj=target,mode='wb',mtime=0) as zipped:zipped.write(stream.read())
backup_sha=hashlib.sha256(backup.read_bytes()).hexdigest()
backup.unlink()
report={'schema':'bean.draw.vps.journal_followup.v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'source_git_sha':run['source_git_sha'],'run_id':run['run_id'],'journal_sha_chain':'verified','draft_rows':2,'run_completion_rows':1,'total_rows':3,'source_file_sha256_before':before,'source_file_sha256_after':after,'backup_sha256':backup_sha,'compressed_sha256':hashlib.sha256((out/'drawing-journal.sqlite3.gz').read_bytes()).hexdigest(),'events':metadata,'retained_context_sha256':hashlib.sha256(context.encode()).hexdigest(),'retained_context_records':len(json.loads(context)),'new_provider_call_made':False,'actual_followup_generation_delivery_tested':False,'primary_private_database_used':False,'correction':'Initial exporter allowed only draft events and withheld this fresh journal because it also contains its legitimate run-completion trial. Original omission receipt is preserved.'}
(out/'verification.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
(out/'export-hashes.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
with tarfile.open(data/'pilot-journal-followup.tar.gz','w:gz') as archive:archive.add(out,arcname=out.name)
print(json.dumps({'draft_rows':2,'run_completion_rows':1,'sha_chain':'verified','source_unchanged':True,'other_private_history_exported':False}))
PY
