// Actual IndexedDB semantics exercised with fake-indexeddb, not DOM-only mocks.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {IDBFactory} from 'fake-indexeddb';
import {
  DeviceMemory, INITIAL_STATE, MAX_PATCHES, appendDemoPatch, applyPatch,
  changes, freshLedger, replayLedger, sha256, verifyPublicManifest
} from '../docs/bean-demo/device-memory.mjs';

function factory() { return new IDBFactory(); }
async function specimenManifest() {
  const value = {
    schema: 'bean.github.invoke.v1',
    synthetic_only: true,
    generation: 4,
    boots: 4,
    events: 107,
    processed_digital_commands: 2,
    source_sha: 'a'.repeat(40),
    databases: {core: {bytes: 1234}}
  };
  value.receipt_sha256 = await sha256(value);
  return value;
}

test('fresh device ledger is recoverable and has an exact SHA tip', async () => {
  const ledger = await freshLedger();
  assert.deepEqual(await replayLedger(ledger), INITIAL_STATE);
  assert.equal(ledger.current_sha256, await sha256(INITIAL_STATE));
});

test('patch replay keeps exactly the same state and detects tampering', async () => {
  let ledger = await freshLedger();
  for (let i = 0; i < 5; i++) ledger = await appendDemoPatch(ledger);
  const state = await replayLedger(ledger);
  assert.equal(state.counters.events, 5);
  assert.equal(state.memory.focus, 'reflection');
  assert.equal(ledger.patches.length, 5);
  const altered = structuredClone(ledger);
  altered.patches[1].patch[0].v = 999999;
  await assert.rejects(() => replayLedger(altered), /hash mismatch|Noncanonical/);
  const reordered = structuredClone(ledger);
  [reordered.patches[0], reordered.patches[1]] = [reordered.patches[1], reordered.patches[0]];
  await assert.rejects(() => replayLedger(reordered), /order|provenance/i);
});

test('patches reject prototype injection and unknown keys', () => {
  assert.throws(() => applyPatch(INITIAL_STATE, [
    {p: ['__proto__'], v: 'x'}]), /Unknown patch field/);
  assert.throws(() => changes(INITIAL_STATE, {...INITIAL_STATE, new_key: 'y'}),
    /cannot silently add or remove/);
});

test('IndexedDB survives close, reopen and repeated local patch updates', async () => {
  const dbFactory = factory();
  const first = await DeviceMemory.open(dbFactory);
  await first.loadLedger();
  await first.recordDemoEvent();
  await first.recordDemoEvent();
  first.close();
  const reopened = await DeviceMemory.open(dbFactory);
  const recovered = await reopened.loadLedger();
  const state = await replayLedger(recovered);
  assert.equal(recovered.revision, 2);
  assert.equal(state.counters.events, 2);
  assert.equal(recovered.patches[1].sequence, 2);
  reopened.close();
});

test('cached GitHub checkpoint is verified before persistence and after recovery', async () => {
  const dbFactory = factory();
  const memory = await DeviceMemory.open(dbFactory);
  const m = await specimenManifest();
  await memory.savePublicReceipt(m);
  memory.close();
  const reopened = await DeviceMemory.open(dbFactory);
  const saved = await reopened.loadPublicReceipt();
  assert.equal(saved.manifest.generation, 4);
  assert.equal(saved.origin, 'github-public-main');
  assert.ok(saved.verified_at);
  saved.manifest.events = 999999;
  await assert.rejects(() => verifyPublicManifest(saved.manifest), /mismatch/);
  await assert.rejects(() => reopened.savePublicReceipt(saved.manifest), /mismatch/);
  reopened.close();
});

test('private note is never in the public manifest and is size-limited', async () => {
  const memory = await DeviceMemory.open(factory());
  await memory.saveNote('One local research observation');
  await memory.savePublicReceipt(await specimenManifest());
  const note = await memory.loadNote();
  const receipt = await memory.loadPublicReceipt();
  assert.equal(note.text, 'One local research observation');
  assert.equal(JSON.stringify(receipt).includes(note.text), false);
  await assert.rejects(() => memory.saveNote('x'.repeat(1601)), /1600/);
  memory.close();
});

test('user-triggered JSON export and import deterministically restore cache', async () => {
  const origin = await DeviceMemory.open(factory());
  await origin.loadLedger();
  await origin.recordDemoEvent();
  await origin.saveNote('synthetic local note');
  await origin.savePublicReceipt(await specimenManifest());
  const data = await origin.exportLocal();
  origin.close();
  const restored = await DeviceMemory.open(factory());
  await restored.importLocal(data);
  assert.equal((await restored.loadLedger()).revision, 1);
  assert.equal((await restored.loadNote()).text, 'synthetic local note');
  assert.equal((await restored.loadPublicReceipt()).manifest.generation, 4);
  await restored.clearAll();
  assert.equal(await restored.loadNote(), null);
  assert.equal(await restored.loadPublicReceipt(), null);
  assert.equal((await restored.loadLedger()).revision, 0);
  restored.close();
});

test('unknown or corrupt import is rejected without replacing live data', async () => {
  const memory = await DeviceMemory.open(factory());
  await memory.loadLedger();
  await memory.recordDemoEvent();
  const valid = await memory.exportLocal();
  const corrupt = structuredClone(valid);
  corrupt.ledger.current_sha256 = 'f'.repeat(64);
  await assert.rejects(() => memory.importLocal(corrupt), /tip hash mismatch/);
  assert.equal((await memory.loadLedger()).revision, 1);
  await assert.rejects(() => memory.importLocal({schema: 'unknown'}), /Unknown/);
  memory.close();
});

test('bounded active cache refuses to silently discard patches', async () => {
  let ledger = await freshLedger();
  for (let i = 0; i < MAX_PATCHES; i++) ledger = await appendDemoPatch(ledger);
  assert.equal(ledger.patches.length, MAX_PATCHES);
  await assert.rejects(() => appendDemoPatch(ledger), /full/);
});

test('IndexedDB absence fails honestly', async () => {
  await assert.rejects(() => DeviceMemory.open(null), /unavailable/);
});


test('all busy-state control IDs exist in the published page', async () => {
  const {readFileSync} = await import('node:fs');
  const ui = readFileSync(new URL('../docs/bean-demo/device-ui.mjs', import.meta.url), 'utf8');
  const html = readFileSync(new URL('../docs/bean-demo/index.html', import.meta.url), 'utf8');
  const section = ui.slice(ui.indexOf('function setBusy'), ui.indexOf('async function showLedger'));
  const ids = new Set([...section.matchAll(/'([a-z]+(?:-[a-z]+)*)'/g)].map(x => x[1]));
  assert.ok(ids.size >= 8, 'Expected real local-memory controls');
  for (const id of ids) assert.ok(html.includes('id="' + id + '"'), 'Missing HTML control: ' + id);
});
