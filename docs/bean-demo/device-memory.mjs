// BEAN public demo: private browser-local, versioned memory cache.
// No networking, cookies, analytics, user identifier or GitHub writes in this module.
// The authoritative Python Core checkpoint remains on GitHub, not in IndexedDB.
export const DB_NAME = 'bean-device-memory';
export const DB_VERSION = 1;
export const LEDGER_SCHEMA = 'bean.device.ledger.v1';
export const EXPORT_SCHEMA = 'bean.device.export.v1';
export const MAX_PATCHES = 128;
export const INITIAL_STATE = Object.freeze({
  identity: 'BEAN',
  environment: 'synthetic',
  mission: 'evidence linked continuity',
  memory: {focus: 'observation', confidence: 0.45, source: 'verified-receipts'},
  counters: {events: 0, successes: 0, failures: 0},
  flags: {unknowns: true, physical_motion: false, provider: false},
  history: 'public-only; archived evidence retained'
});
const KEY_LEDGER = 'demo-ledger';
const KEY_NOTE = 'local-note';
const KEY_RECEIPT = 'public-receipt';
const encoder = new TextEncoder();

export function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
function assert(condition, text) {
  if (!condition) throw new Error(text);
}
export function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])]));
  }
  return value;
}
export function jsonBytes(value) {
  return encoder.encode(JSON.stringify(value)).length;
}
export async function sha256(value) {
  const input = typeof value === 'string' ? value : JSON.stringify(stable(value));
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(input));
  return Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, '0')).join('');
}
function same(a, b) {
  return JSON.stringify(stable(a)) === JSON.stringify(stable(b));
}
export function changes(previous, next, path = []) {
  const output = [];
  assert(previous && next && typeof previous === 'object' &&
    typeof next === 'object' && !Array.isArray(previous) && !Array.isArray(next),
    'Dictionary patch requires two objects');
  const oldKeys = Object.keys(previous).sort();
  const newKeys = Object.keys(next).sort();
  assert(same(oldKeys, newKeys), 'Patch cannot silently add or remove fields');
  for (const key of newKeys) {
    assert(!['__proto__', 'prototype', 'constructor'].includes(key), 'Unsafe patch field');
    const before = previous[key], after = next[key];
    if (before && after && typeof before === 'object' && !Array.isArray(before) &&
        typeof after === 'object' && !Array.isArray(after)) {
      output.push(...changes(before, after, [...path, key]));
    } else if (!same(before, after)) {
      output.push({p: [...path, key], v: clone(after)});
    }
  }
  return output;
}
export function applyPatch(previous, patch) {
  assert(Array.isArray(patch) && patch.length <= 32, 'Invalid patch size');
  const next = clone(previous);
  for (const op of patch) {
    assert(op && Object.keys(op).sort().join(',') === 'p,v' &&
      Array.isArray(op.p) && op.p.length >= 1 && op.p.length <= 6,
      'Invalid patch operation');
    let parent = next;
    for (const key of op.p.slice(0, -1)) {
      assert(typeof key === 'string' && Object.prototype.hasOwnProperty.call(parent, key) &&
        !['__proto__', 'prototype', 'constructor'].includes(key) &&
        parent[key] && typeof parent[key] === 'object' && !Array.isArray(parent[key]),
        'Invalid patch path');
      parent = parent[key];
    }
    const leaf = op.p[op.p.length - 1];
    assert(typeof leaf === 'string' && Object.prototype.hasOwnProperty.call(parent, leaf) &&
      !['__proto__', 'prototype', 'constructor'].includes(leaf), 'Unknown patch field');
    assert(typeof op.v !== 'object' || op.v === null, 'Only scalar patch values accepted');
    parent[leaf] = op.v;
  }
  return next;
}
export function nextDemoState(current) {
  const next = clone(current);
  const n = current.counters.events + 1;
  next.counters.events = n;
  next.counters.successes = Math.floor(n / 3);
  next.counters.failures = n - next.counters.successes;
  next.memory.focus = n % 2 ? 'reflection' : 'consolidation';
  next.memory.confidence = Math.round((0.45 + n * 0.01) * 100) / 100;
  return next;
}
export async function freshLedger() {
  return {
    schema: LEDGER_SCHEMA,
    revision: 0,
    base: clone(INITIAL_STATE),
    base_sha256: await sha256(INITIAL_STATE),
    current_sha256: await sha256(INITIAL_STATE),
    patches: [],
    updated_at: new Date().toISOString()
  };
}
export async function replayLedger(ledger) {
  assert(ledger && ledger.schema === LEDGER_SCHEMA && Number.isSafeInteger(ledger.revision) &&
    ledger.revision >= 0 && Array.isArray(ledger.patches) &&
    ledger.patches.length <= MAX_PATCHES && ledger.revision === ledger.patches.length,
    'Invalid browser ledger envelope');
  assert(same(ledger.base, INITIAL_STATE), 'Ledger base does not match known synthetic state');
  assert(ledger.base_sha256 === await sha256(ledger.base), 'Base hash mismatch');
  let current = clone(ledger.base);
  let previous = ledger.base_sha256;
  for (let i = 0; i < ledger.patches.length; i++) {
    const row = ledger.patches[i];
    assert(row && row.schema === 'bean.device.patch.v1' &&
      row.sequence === i + 1 && row.before_sha256 === previous &&
      typeof row.after_sha256 === 'string', 'Patch order or provenance mismatch');
    const after = applyPatch(current, row.patch);
    assert(same(changes(current, after), row.patch), 'Noncanonical patch operation');
    const digest = await sha256(after);
    assert(digest === row.after_sha256, 'Patch hash mismatch at event ' + (i + 1));
    current = after;
    previous = digest;
  }
  assert(ledger.current_sha256 === previous, 'Ledger tip hash mismatch');
  return current;
}
export async function appendDemoPatch(ledger) {
  const current = await replayLedger(ledger);
  assert(ledger.patches.length < MAX_PATCHES, 'Local cache is full; export, then clear to restart');
  const next = nextDemoState(current);
  const patch = changes(current, next);
  const row = {
    schema: 'bean.device.patch.v1',
    sequence: ledger.patches.length + 1,
    before_sha256: ledger.current_sha256,
    after_sha256: await sha256(next),
    patch,
    at: new Date().toISOString()
  };
  return {
    ...ledger,
    revision: ledger.revision + 1,
    patches: [...ledger.patches, row],
    current_sha256: row.after_sha256,
    updated_at: new Date().toISOString()
  };
}
export async function verifyPublicManifest(manifest) {
  assert(manifest && typeof manifest === 'object' && !Array.isArray(manifest) &&
    manifest.schema === 'bean.github.invoke.v1' && manifest.synthetic_only === true &&
    Number.isSafeInteger(manifest.generation) && manifest.generation >= 1 &&
    typeof manifest.receipt_sha256 === 'string' &&
    /^[a-f0-9]{64}$/.test(manifest.receipt_sha256) &&
    manifest.databases && manifest.databases.core &&
    typeof manifest.databases.core.bytes === 'number',
    'Public checkpoint receipt has an unexpected schema');
  const copy = {...manifest};
  delete copy.receipt_sha256;
  assert(await sha256(copy) === manifest.receipt_sha256, 'Public checkpoint SHA-256 mismatch');
  return true;
}
function fromRequest(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('IndexedDB request failed'));
  });
}
function transactionDone(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted'));
    tx.onerror = () => reject(tx.error || new Error('IndexedDB transaction failed'));
  });
}
export function openDatabase(indexedDBFactory = globalThis.indexedDB) {
  if (!indexedDBFactory) return Promise.reject(new Error('IndexedDB unavailable'));
  return new Promise((resolve, reject) => {
    const request = indexedDBFactory.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('records')) db.createObjectStore('records', {keyPath: 'key'});
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Cannot open IndexedDB'));
    request.onblocked = () => reject(new Error('IndexedDB is blocked by another tab'));
  });
}
export class DeviceMemory {
  constructor(db) { this.db = db; }
  static async open(factory) { return new DeviceMemory(await openDatabase(factory)); }
  async get(key) {
    const tx = this.db.transaction('records', 'readonly');
    const result = await fromRequest(tx.objectStore('records').get(key));
    return result ? result.value : null;
  }
  async put(key, value) {
    const tx = this.db.transaction('records', 'readwrite');
    const done = transactionDone(tx);
    tx.objectStore('records').put({key, value});
    await done;
    return value;
  }
  async loadLedger() {
    let ledger = await this.get(KEY_LEDGER);
    if (!ledger) {
      ledger = await freshLedger();
      // Simultaneous first loads may race. Read back the committed canonical value.
      const tx = this.db.transaction('records', 'readwrite');
      const done = transactionDone(tx);
      const store = tx.objectStore('records');
      const present = await fromRequest(store.get(KEY_LEDGER));
      if (!present) store.put({key: KEY_LEDGER, value: ledger});
      await done;
      ledger = await this.get(KEY_LEDGER);
    }
    await replayLedger(ledger);
    return ledger;
  }
  async recordDemoEvent() {
    const ledger = await this.loadLedger();
    const next = await appendDemoPatch(ledger);
    const tx = this.db.transaction('records', 'readwrite');
    const done = transactionDone(tx);
    const store = tx.objectStore('records');
    const prior = await fromRequest(store.get(KEY_LEDGER));
    if (!prior || prior.value.current_sha256 !== ledger.current_sha256 ||
      prior.value.revision !== ledger.revision) {
      tx.abort();
      try { await done; } catch (_) { /* expected optimistic-concurrency abort */ }
      throw new Error('Another tab updated BEAN memory. Reload and retry.');
    }
    store.put({key: KEY_LEDGER, value: next});
    await done;
    return next;
  }
  async resetLedger() { return this.put(KEY_LEDGER, await freshLedger()); }
  async saveNote(value) {
    assert(typeof value === 'string' && value.length <= 1600, 'Note must be 1600 characters or less');
    return this.put(KEY_NOTE, {text: value, updated_at: new Date().toISOString()});
  }
  async loadNote() {
    const note = await this.get(KEY_NOTE);
    assert(!note || (typeof note.text === 'string' && note.text.length <= 1600),
      'Invalid stored note');
    return note;
  }
  async savePublicReceipt(manifest) {
    await verifyPublicManifest(manifest);
    return this.put(KEY_RECEIPT, {
      manifest: clone(manifest),
      verified_at: new Date().toISOString(),
      origin: 'github-public-main'
    });
  }
  async loadPublicReceipt() {
    const cached = await this.get(KEY_RECEIPT);
    if (!cached) return null;
    await verifyPublicManifest(cached.manifest);
    assert(cached.origin === 'github-public-main', 'Unknown public source');
    return cached;
  }
  async exportLocal() {
    const ledger = await this.loadLedger();
    const note = await this.loadNote();
    const receipt = await this.loadPublicReceipt();
    return {
      schema: EXPORT_SCHEMA,
      exported_at: new Date().toISOString(),
      ledger,
      note,
      public_receipt: receipt
    };
  }
  async importLocal(data) {
    assert(data && data.schema === EXPORT_SCHEMA, 'Unknown BEAN device export format');
    await replayLedger(data.ledger);
    assert(!data.note || (typeof data.note.text === 'string' && data.note.text.length <= 1600),
      'Invalid device note');
    if (data.public_receipt) {
      await verifyPublicManifest(data.public_receipt.manifest);
      assert(data.public_receipt.origin === 'github-public-main', 'Unknown public source');
    }
    const tx = this.db.transaction('records', 'readwrite');
    const done = transactionDone(tx);
    const store = tx.objectStore('records');
    store.put({key: KEY_LEDGER, value: clone(data.ledger)});
    store.put({key: KEY_NOTE, value: data.note ? clone(data.note) : {text: '', updated_at: ''}});
    if (data.public_receipt) store.put({key: KEY_RECEIPT, value: clone(data.public_receipt)});
    else store.delete(KEY_RECEIPT);
    await done;
    return data.ledger;
  }
  async clearAll() {
    const tx = this.db.transaction('records', 'readwrite');
    const done = transactionDone(tx);
    tx.objectStore('records').clear();
    await done;
  }
  close() { this.db.close(); }
}
