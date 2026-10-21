"""BEAN research: byte-recoverable compressed test ledger with disposable indexed cache.

Archives are the truth, SQLite is a rebuilt acceleration index. No model output
may alter a source record or assert that a test passed without original evidence.
"""
from __future__ import annotations

import base64
from contextlib import closing
import gzip
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = 'bean.recall.v1'
RUN_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')


def encode(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                      sort_keys=True, allow_nan=False).encode('utf-8')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def junit_events(source: bytes) -> list[dict]:
    """Keep byte-identical JUnit input and each searchable testcase, including failures."""
    root = ET.fromstring(source)
    cases = []
    for case in root.iter('testcase'):
        status = ('failed' if case.find('failure') is not None else
                  'error' if case.find('error') is not None else
                  'skipped' if case.find('skipped') is not None else 'passed')
        cases.append({'kind':'test', 'name':f"{case.get('classname','')}::{case.get('name','')}",
                      'status':status,'xml':ET.tostring(case,encoding='unicode')})
    return [{'kind':'attachment','name':'junit-original.xml',
             'data_b64':base64.b64encode(source).decode('ascii'),
             'sha256':sha(source)}] + cases


class IndexedLedger:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.archive = self.root / 'archive'
        self.cache = self.root / 'index.sqlite'

    def append(self, run: str, events: list[dict]) -> dict:
        """Create one immutable archive; same-byte retries are idempotent."""
        if not isinstance(run, str) or not RUN_PATTERN.fullmatch(run):
            raise ValueError('unsafe run id')
        if not isinstance(events, list) or not events:
            raise ValueError('events required')
        rows = []
        items = []
        for seq, event in enumerate(events):
            if not isinstance(event, dict) or not isinstance(event.get('name'),str):
                raise ValueError('invalid event')
            if event.get('kind') not in ('test','attachment'):
                raise ValueError('invalid event kind')
            if event['kind']=='test' and event.get('status') not in ('passed','failed','skipped','error'):
                raise ValueError('invalid test status')
            digest = sha(encode(event))
            ident = 'T.'+sha(encode([run,seq,digest]))[:24]
            rows.append({'id':ident, 'event_sha256':digest,'event':event})
            items.append({'id':ident,'sha256':digest,'kind':event['kind'],'name':event['name']})
        content = b''.join(encode(row)+b'\n' for row in rows)
        compressed = gzip.compress(content, compresslevel=6, mtime=0)
        manifest = {'schema':VERSION,'run':run,'count':len(rows),'archive_sha256':sha(compressed),
                    'content_sha256':sha(content),'items':items}
        doc = encode(manifest)+b'\n'
        path = self.archive / f'{run}.jsonl.gz'
        meta = self.archive / f'{run}.manifest.json'
        if path.exists() or meta.exists():
            if not (path.exists() and meta.exists() and path.read_bytes()==compressed
                    and meta.read_bytes()==doc):
                raise ValueError('immutable run conflict')
            return manifest
        _atomic(path, compressed)
        _atomic(meta,doc)
        return manifest

    def rebuild(self) -> int:
        """Validate all compressed archives and regenerate entire SQLite cache."""
        self.root.mkdir(parents=True,exist_ok=True)
        fd,temp = tempfile.mkstemp(prefix='index-',suffix='.sqlite',dir=self.root)
        os.close(fd)
        db = sqlite3.connect(temp)
        try:
            db.executescript('''CREATE TABLE events(
                id TEXT PRIMARY KEY, run TEXT NOT NULL, ordinal INTEGER NOT NULL,
                name TEXT NOT NULL, kind TEXT NOT NULL, status TEXT,
                event_sha256 TEXT NOT NULL, event_json BLOB NOT NULL);
                CREATE INDEX events_run ON events(run,name);''')
            count = 0
            archives = {x.name[:-9] for x in self.archive.glob('*.jsonl.gz')}
            manifests = {x.name[:-14] for x in self.archive.glob('*.manifest.json')}
            if archives != manifests:
                raise ValueError('orphaned archive or missing manifest')
            for meta in sorted(self.archive.glob('*.manifest.json')):
                manifest = json.loads(meta.read_bytes())
                run = manifest['run']
                if not RUN_PATTERN.fullmatch(run) or meta.name != f'{run}.manifest.json' or manifest['schema'] != VERSION:
                    raise ValueError('invalid run manifest')
                blob = (self.archive / f'{run}.jsonl.gz').read_bytes()
                if sha(blob)!=manifest['archive_sha256']:
                    raise ValueError(f'archive hash mismatch: {run}')
                data = gzip.decompress(blob)
                if sha(data)!=manifest['content_sha256']:
                    raise ValueError(f'content hash mismatch: {run}')
                lines=data.splitlines()
                if len(lines)!=manifest['count'] or len(lines)!=len(manifest['items']):
                    raise ValueError(f'missing records in: {run}')
                for seq,(line,item) in enumerate(zip(lines,manifest['items'])):
                    record=json.loads(line)
                    event=record['event']
                    if encode(record)!=line or sha(encode(event))!=record['event_sha256']:
                        raise ValueError('corrupt event')
                    if (record['id']!=item['id'] or record['event_sha256']!=item['sha256'] or
                        item['kind']!=event['kind'] or item['name']!=event['name'] or
                        record['id']!='T.'+sha(encode([run,seq,item['sha256']]))[:24]):
                        raise ValueError('manifest mismatch')
                    db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',
                               (record['id'],run,seq,event['name'],event['kind'],
                                event.get('status'),item['sha256'],encode(event)))
                    count+=1
            db.commit()
            db.close()
            os.replace(temp,self.cache)
            return count
        finally:
            try: db.close()
            except Exception: pass
            if os.path.exists(temp): os.unlink(temp)

    def get(self, identifier: str) -> dict:
        """Fast lookup from rebuilt index, verifying original payload hash."""
        with closing(sqlite3.connect(self.cache)) as db:
            row=db.execute('SELECT event_sha256,event_json FROM events WHERE id=?',(identifier,)).fetchone()
        if row is None:
            raise KeyError(identifier)
        if sha(row[1])!=row[0]:
            raise ValueError('index payload hash mismatch')
        return json.loads(row[1])

    def ids(self, *, run: str | None = None, name: str | None = None) -> list[str]:
        where,params=[],[]
        if run is not None:
            where.append('run=?');params.append(run)
        if name is not None:
            where.append('name=?');params.append(name)
        with closing(sqlite3.connect(self.cache)) as db:
            sql='SELECT id FROM events'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY run,ordinal'
            return [r[0] for r in db.execute(sql,params)]

    def scoreboard(self) -> dict:
        with closing(sqlite3.connect(self.cache)) as db:
            pairs=db.execute("SELECT run,status,count(*) FROM events WHERE kind='test' GROUP BY run,status ORDER BY run,status").fetchall()
        per={}
        for run,status,count in pairs:
            per.setdefault(run,{})[status]=count
        return {'schema':VERSION,'runs':per,'test_cases':sum(c for _,_,c in pairs)}

    def original_junit(self, run: str) -> bytes:
        ids=self.ids(run=run,name='junit-original.xml')
        if len(ids)!=1:
            raise ValueError('JUnit attachment missing or ambiguous')
        event=self.get(ids[0]);raw=base64.b64decode(event['data_b64'],validate=True)
        if sha(raw)!=event['sha256']:
            raise ValueError('JUnit attachment hash mismatch')
        return raw


def linear_lookup(gz_path: Path, identifier: str) -> dict:
    """Unindexed scan used only as benchmark baseline and independent comparator."""
    for line in gzip.decompress(gz_path.read_bytes()).splitlines():
        row=json.loads(line)
        if row['id']==identifier:
            return row['event']
    raise KeyError(identifier)
