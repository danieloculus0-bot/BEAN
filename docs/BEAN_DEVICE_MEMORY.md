# Public BEAN demo: device-local memory and offline cache

Status: implemented **browser-level** memory, not native Python Core memory or remote
ChatGPT synchronization. Source is public under docs/bean-demo/ and the published
demo is https://danieloculus0-bot.github.io/BEAN/bean-demo/.

## What is on a visitor's device

- IndexedDB database: bean-device-memory (schema version 1). Records are stored
  under the GitHub Pages site origin, not sent to GitHub in API requests.
- An initial **synthetic** BEAN demonstration state plus up to 128 ordered
  dictionary patches. Each patch records its sequence, prior SHA-256 state
  digest and next SHA-256 state digest. Replay verifies the known initial
  state, every previous link and the final digest before rendering.
- One optional 1,600-character device-only research note, saved only on
  explicit button press. It is not the Python Core's SQLite memory.
- The latest successfully verified public synthetic BEAN checkpoint manifest,
  fetched read-only from GitHub main. Cached receipts are re-verified before
  offline display. Offline views say CACHE and keep the original retrieval
  date; they never claim to be current or to know live Core status.

The storage is deliberately small. After 128 patches BEAN stops recording
instead of silently discarding old events. Users can manually export JSON,
clear this particular demo's data, and import a previous export. Import checks
the ledger before atomically replacing cache contents. Browser storage is not a
durable backup and can be evicted by the OS, browser cleanup or private mode.
IndexedDB contents are not encrypted by this application. Other same-origin
scripts may be able to access the database, so do not store secrets.

## Offline install

A scope-limited service worker caches the public demo's HTML, JavaScript,
manifest and existing BEAN avatar. The web app manifest advertises an optional
installable standalone view. After the first successful installation, repeat
visits to the demo can load the shell offline. The public GitHub manifest itself
is not in the service worker cache: that verified data is saved separately in
IndexedDB so the page can say precisely when it was last retrieved.

If IndexedDB is not supported, blocked or corrupted, the page labels the
ledger as session-only and disables save, import, export and delete controls.
No silent fallback to cookies, localStorage, GitHub or a third-party cloud.

## ChatGPT and GitHub boundary

There is **no automatic upload** of local notes, prompts or patch history.
An explicit Copy Context button can place a small private handoff JSON packet
onto the user's clipboard for a private ChatGPT conversation. The packet
contains the optional local note and a public receipt reference, not the full
Python Core state. The public GitHub Issues bridge continues to accept only
synthetic/public-safe commands with its separate verified contract.

This feature does not make a user's phone a remotely accessible server, does
not connect the native Jetson Core, and does not establish consciousness or
neural training. Any future bidirectional private synchronization requires
an authenticated private service and a separate reviewed transport protocol.

## Verification

- Offline Node/IndexedDB: node --test tests/test_bean_device_memory.mjs
  (with pinned fake-indexeddb dev test dependency installed).
- Browser module/service worker static syntax checked by Node 22.
- Public route/website integrity:
  python -m unittest discover -s tests -p 'test_ecosystem_navigation.py' -v
- CI: .github/workflows/bean-device-memory.yml

Failure behaviors are tested: altered patch hashes, reordered sequence, unknown
fields, corrupt import, public receipt tampering, deleted cache, missing
IndexedDB, persisted restart and bounded event retention. This is browser
storage evidence, not evidence of neural learning or Core integration.
