# BEAN offline visual recall (experimental)

An **offline, local-only photo evidence index** for the BEAN ecosystem. It accepts a timestamped JSON manifest and frames already extracted from a user-owned video, stores searchable frame/room metadata in SQLite FTS5, and retains file-level SHA-256 and 64-bit average hashes.

This tool is **not** a neural vision model, a video captioner, a speech-to-text engine, or an integrated BEAN Core memory API. Scene tags and descriptions must be supplied as evidence by the caller, and the caller must keep all corresponding imagery in a private local directory. BEAN's separate hosted memory adapter cannot fetch these images.

## Requirements

Python 3.10+, Pillow, SQLite with FTS5.

```sh
python -m pip install Pillow
python tools/visual_memory/bean_visual_recall.py build --manifest /path/to/private/visual_memory.json --db /path/to/private/bean_visual_index.sqlite3
python tools/visual_memory/bean_visual_recall.py search "dining table" --db /path/to/private/bean_visual_index.sqlite3
python tools/visual_memory/bean_visual_recall.py similar /path/to/private/frames_full/frame_026s.jpg --db /path/to/private/bean_visual_index.sqlite3
python tools/visual_memory/bean_visual_recall.py verify --db /path/to/private/bean_visual_index.sqlite3
python -m unittest discover -s tools/visual_memory -p 'test_*.py'
```

Pass a real manifest with `capture_id`, `source.filename`, `source.sha256`, `source.duration_seconds`, `scenes[]` (id/name/start/end/description/confidence), and `frames.items[]` (t_seconds, room_id, caption, full_frame, thumbnail). Each image filename must be relative to and stay within the manifest's directory. The index stores relative paths and content hashes. Original images are not embedded in SQLite; preserve the source directory with its video images.

## Integrity and limits

- Rebuilding a capture is idempotent and does not mint new memory from repeated observations.
- `verify` re-hashes both native screenshots and thumbnails to detect missing or altered files.
- `similar` compares 64-bit average hashes using Hamming distance. This detects visual resemblance, **not** semantic identity or room understanding.
- `search` matches human- or model-supplied text labels; it does not automatically recognize pictured objects.
- The caller must supply source attribution and label uncertainty. Capture time alone does not prove geometry, cardinal orientation or floorplan scale.
- No private video, home images, location, user audio, or generated personal manifests are committed to this public repository.

## Evidence

Initial local tests (synthetic red/green screenshots): 2/2 passing, covering import, FTS retrieval, hash similarity, re-import, SHA-256 tamper detection, and rejection of path traversal. A separate private walkthrough index demonstrated 76 frame entries and 152 verified full/thumbnail files, but no user media or private metadata is included here.

This is a standalone tool. Wiring it into an authorized BEAN Core host and independently validating automatic visual labeling and transcript alignment are future integration tasks.
