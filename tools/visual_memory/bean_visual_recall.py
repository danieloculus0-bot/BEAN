"""BEAN Visual Recall v0.1: offline, evidence-linked photo retrieval.

This indexes real images on disk using scene labels and a perceptual hash.
It DOES NOT infer scene semantics, speech, an exact floorplan, or consciousness.
Images remain private and local. Requires Python 3.10+, Pillow, SQLite FTS5.

Usage:
  python bean_visual_recall.py build --manifest visual_memory.json
  python bean_visual_recall.py search 'dining table'
  python bean_visual_recall.py similar frames_full/frame_026s.jpg
  python bean_visual_recall.py verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from PIL import Image

DB_NAME = "bean_visual_index.sqlite3"


def _safe_path(base: Path, filename: str) -> Path:
    """Never index paths outside the explicit archive root."""
    base = base.resolve()
    p = (base / filename).resolve()
    if not p.is_relative_to(base) or not p.is_file():
        raise ValueError(f"Missing or unsafe image path: {filename}")
    return p


def _image_ahash(path: Path) -> str:
    """Deterministic 64-bit average hash for near-duplicate retrieval.

    This is NOT a semantic image embedding. Different views of one room
    may not match; matching textures do not prove identical objects.
    """
    with Image.open(path) as im:
        gray = im.convert("L").resize((8, 8))
        g = list(gray.get_flattened_data() if hasattr(gray, "get_flattened_data") else gray.getdata())
    mean = sum(g) / 64
    n = 0
    for x in g:
        n = (n << 1) | (x >= mean)
    return f"{n:016x}"


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS captures (
        capture_id TEXT PRIMARY KEY,
        source_name TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        duration_s REAL NOT NULL,
        manifest_sha256 TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS scenes (
        capture_id TEXT NOT NULL REFERENCES captures(capture_id),
        scene_id TEXT NOT NULL,
        room TEXT NOT NULL, start_s REAL NOT NULL, end_s REAL NOT NULL,
        description TEXT NOT NULL, confidence TEXT NOT NULL,
        PRIMARY KEY(capture_id,scene_id)
    );
    CREATE TABLE IF NOT EXISTS frames (
        id INTEGER PRIMARY KEY,
        capture_id TEXT NOT NULL REFERENCES captures(capture_id),
        t_seconds REAL NOT NULL,
        room_id TEXT NOT NULL,
        caption TEXT NOT NULL,
        full_relative_path TEXT NOT NULL,
        thumbnail_relative_path TEXT NOT NULL,
        full_sha256 TEXT NOT NULL,
        thumbnail_sha256 TEXT NOT NULL,
        ahash64 TEXT NOT NULL,
        UNIQUE(capture_id,t_seconds)
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS frame_fts USING fts5(
        caption,room,description, tokenize='unicode61'
    );
    CREATE INDEX IF NOT EXISTS idx_frames_time ON frames(capture_id,t_seconds);
    CREATE INDEX IF NOT EXISTS idx_frames_room ON frames(room_id);
    """)
    return conn


def build(manifest: Path, db: Path | None = None) -> dict:
    manifest = manifest.resolve()
    base = manifest.parent
    d = json.loads(manifest.read_text(encoding="utf-8"))
    db = db or base / DB_NAME
    conn = connect(db)
    capture_id = d["capture_id"]
    scene_lookup = {s["id"]: s for s in d["scenes"]}
    count = 0
    try:
        with conn:
            conn.execute("""INSERT INTO captures VALUES (?,?,?,?,?)
                ON CONFLICT(capture_id) DO UPDATE SET
                source_name=excluded.source_name,source_sha256=excluded.source_sha256,
                duration_s=excluded.duration_s,manifest_sha256=excluded.manifest_sha256""",
                (capture_id,d["source"]["filename"],d["source"]["sha256"],
                 d["source"]["duration_seconds"],hashlib.sha256(manifest.read_bytes()).hexdigest()))
            conn.execute("DELETE FROM frame_fts WHERE rowid IN (SELECT id FROM frames WHERE capture_id=?)", (capture_id,))
            conn.execute("DELETE FROM frames WHERE capture_id=?",(capture_id,))
            conn.execute("DELETE FROM scenes WHERE capture_id=?",(capture_id,))
            for s in d["scenes"]:
                conn.execute("INSERT INTO scenes VALUES (?,?,?,?,?,?,?)",
                    (capture_id,s["id"],s["name"],s["start"],s["end"],s["description"],s["confidence"]))
            for f in d["frames"]["items"]:
                full = _safe_path(base,f["full_frame"])
                thumb = _safe_path(base,f["thumbnail"])
                room=scene_lookup[f["room_id"]]
                sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
                cur=conn.execute("""INSERT INTO frames(capture_id,t_seconds,room_id,caption,full_relative_path,
                    thumbnail_relative_path,full_sha256,thumbnail_sha256,ahash64) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (capture_id,f["t_seconds"],f["room_id"],f["caption"],
                     f["full_frame"],f["thumbnail"],sha(full),sha(thumb),_image_ahash(full)))
                conn.execute("INSERT INTO frame_fts(rowid,caption,room,description) VALUES(?,?,?,?)",
                    (cur.lastrowid,f["caption"],room["name"],room["description"]))
                count+=1
    finally:
        conn.close()
    return {"database": str(db), "capture_id": capture_id, "indexed_frames": count,
            "scenes": len(scene_lookup), "inference": "none; captions are provided evidence labels"}


def search(db: Path, query: str, limit: int = 15) -> list[dict]:
    conn=connect(db)
    terms=[t.strip() for t in query.split() if t.strip()]
    if not terms: return []
    # Quoted FTS terms prevent query syntax injection; each term is an independent token.
    match=" AND ".join('"'+t.replace('"','""')+'"' for t in terms)
    try:
        rows=conn.execute("""SELECT frames.*,bm25(frame_fts) AS rank FROM frame_fts
            JOIN frames ON frames.id=frame_fts.rowid WHERE frame_fts MATCH ?
            ORDER BY rank,frames.t_seconds LIMIT ?""", (match,limit)).fetchall()
        if not rows:
            rows=conn.execute("""SELECT * FROM frames WHERE lower(caption) LIKE ? OR lower(room_id) LIKE ?
                ORDER BY t_seconds LIMIT ?""",(f'%{query.lower()}%',f'%{query.lower()}%',limit)).fetchall()
        return [{k:r[k] for k in r.keys()} for r in rows]
    finally: conn.close()


def similar(db: Path, path: Path, limit: int = 10) -> list[dict]:
    h=int(_image_ahash(path),16)
    conn=connect(db)
    rows=conn.execute("SELECT id,t_seconds,caption,room_id,ahash64,full_relative_path FROM frames").fetchall()
    conn.close()
    out=[]
    for r in rows:
        d={k:r[k] for k in r.keys()}
        d["hamming_distance"]=(h^int(r["ahash64"],16)).bit_count()
        out.append(d)
    return sorted(out,key=lambda x:(x["hamming_distance"],x["t_seconds"]))[:limit]


def verify(db:Path) -> dict:
    conn=connect(db)
    rows=conn.execute("SELECT * FROM frames ORDER BY t_seconds").fetchall()
    conn.close()
    bad=[]
    root=db.parent.resolve()
    for r in rows:
        for pathcol,hashcol in [('full_relative_path','full_sha256'),('thumbnail_relative_path','thumbnail_sha256')]:
            try:
                path=_safe_path(root,r[pathcol])
                if hashlib.sha256(path.read_bytes()).hexdigest()!=r[hashcol]:
                    bad.append({"id":r['id'],"file":r[pathcol],"error":"SHA-256 mismatch"})
            except ValueError:
                bad.append({"id":r['id'],"file":r[pathcol],"error":"missing/unsafe"})
    return {"frames_checked":len(rows),"image_files_checked":len(rows)*2,"bad_files":bad,"ok":not bad}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=('build','search','similar','verify','rooms'))
    ap.add_argument('value',nargs='?')
    ap.add_argument('--manifest',type=Path,default=Path(__file__).with_name('visual_memory.json'))
    ap.add_argument('--db',type=Path,default=Path(__file__).with_name(DB_NAME))
    ap.add_argument('--limit',type=int,default=15)
    a=ap.parse_args()
    if a.command=='build': result=build(a.manifest,a.db)
    elif a.command=='search': result=search(a.db,a.value or '',a.limit)
    elif a.command=='similar': result=similar(a.db,Path(a.value),a.limit)
    elif a.command=='verify':result=verify(a.db)
    else:
        c=connect(a.db)
        result=[dict(x) for x in c.execute('SELECT * FROM scenes ORDER BY start_s')]
        c.close()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()