// BEAN device-memory UI: local storage only. No automatic user-data uploads.
// GitHub checkpoint fetch is a public, read-only request by the existing demo.
import {
  DeviceMemory, INITIAL_STATE, freshLedger, appendDemoPatch, replayLedger,
  jsonBytes, clone, applyPatch, verifyPublicManifest
} from './device-memory.mjs';

const $ = id => document.getElementById(id);
const MANIFEST_URL = 'https://raw.githubusercontent.com/danieloculus0-bot/BEAN/main/research/github_brain/manifest.json';
let memory = null;
let ledger = null;
let localNote = null;
let latestReceipt = null;
let busy = false;

function message(id, value, kind) {
  const node = $(id);
  node.textContent = value;
  node.className = 'status' + (kind ? ' ' + kind : '');
}
function byteString(n) {
  return n.toLocaleString() + ' B';
}
function setBusy(value) {
  busy = value;
  for (const id of ['step', 'reset', 'verify', 'save-note', 'export-device', 'import-device',
    'copy-context', 'clear-device']) {
    const requiresDatabase = ['save-note', 'export-device', 'import-device', 'clear-device'].includes(id);
    $(id).disabled = value || (requiresDatabase && !memory);
  }
}
async function showLedger() {
  const current = await replayLedger(ledger);
  let full = jsonBytes(ledger.base), compact = jsonBytes(ledger.base);
  let running = clone(ledger.base);
  const lines = [];
  for (const event of ledger.patches) {
    running = applyPatch(running, event.patch);
    full += jsonBytes(running);
    compact += jsonBytes(event.patch);
    lines.push('Event ' + event.sequence + ': ' + JSON.stringify(event.patch));
  }
  $('steps').textContent = ledger.patches.length.toLocaleString();
  $('full').textContent = byteString(full);
  $('compact').textContent = byteString(compact);
  $('patch-log').textContent = lines.slice(-6).join('\n') || 'Nothing recorded yet on this device.';
  $('patch-status').textContent = 'SHA-256 replay verified through event ' +
    ledger.revision + '. Current focus: ' + current.memory.focus +
    '. ' + (memory ? 'Saved in IndexedDB.' : 'Session-only fallback.');
  $('patch-status').className = 'status good';
}
function showNote() {
  $('local-note').value = localNote && localNote.text || '';
  $('note-saved').textContent = localNote && localNote.updated_at ?
    'Saved on this device: ' + new Date(localNote.updated_at).toLocaleString() :
    'No device note saved.';
}
function renderReceipt(m, source, date) {
  for (const [id,key] of [['g','generation'],['b','boots'],['e','events'],
    ['c','processed_digital_commands']]) $(id).textContent = Number(m[key]).toLocaleString();
  $('source').textContent = m.source_sha || 'unknown';
  $('hash').textContent = m.receipt_sha256;
  $('previous').textContent = m.previous_receipt_sha256 || 'first generation';
  $('bytes').textContent = Number(m.databases.core.bytes).toLocaleString() + ' (not compressed)';
  if (source === 'cached') {
    message('receipt-status',
      'OFFLINE / cached verified public receipt from ' + new Date(date).toLocaleString() +
      '. Not confirmed as the latest GitHub state.', 'good');
  } else {
    message('receipt-status',
      'Live public GitHub receipt verified by SHA-256, then cached locally.', 'good');
  }
}
async function refreshPublicReceipt() {
  message('receipt-status', 'Checking public GitHub checkpoint…');
  try {
    const response = await fetch(MANIFEST_URL + '?v=' + Date.now(), {cache: 'no-store'});
    if (!response.ok) throw new Error('GitHub HTTP ' + response.status);
    const manifest = await response.json();
    await verifyPublicManifest(manifest);
    latestReceipt = manifest;
    if (memory) await memory.savePublicReceipt(manifest);
    renderReceipt(manifest, 'network');
  } catch (error) {
    try {
      const cached = memory ? await memory.loadPublicReceipt() : null;
      if (!cached) throw new Error('No verified browser checkpoint saved');
      latestReceipt = cached.manifest;
      renderReceipt(cached.manifest, 'cached', cached.verified_at);
    } catch (cacheError) {
      message('receipt-status',
        'Live receipt unavailable (' + error.message + '). ' + cacheError.message, 'bad');
    }
  }
}
async function doEvent() {
  if (busy) return;
  setBusy(true);
  try {
    ledger = memory ? await memory.recordDemoEvent() : await appendDemoPatch(ledger);
    await showLedger();
  } catch (error) {
    message('patch-status', 'Cannot record event: ' + error.message, 'bad');
  } finally { setBusy(false); }
}
async function doReset() {
  if (busy) return;
  if (ledger.patches.length && !confirm('Reset the local synthetic patch history? Export first if you want to keep it.')) return;
  setBusy(true);
  try {
    ledger = memory ? await memory.resetLedger() : await freshLedger();
    await showLedger();
  } catch (error) { message('patch-status', error.message, 'bad'); }
  finally { setBusy(false); }
}
async function doVerify() {
  try {
    await replayLedger(ledger);
    message('patch-status',
      'REPLAY PASS: ' + ledger.patches.length + ' persisted transitions reproduce the exact state.',
      'good');
  } catch (error) { message('patch-status', 'REPLAY FAILED: ' + error.message, 'bad'); }
}
async function saveLocalNote() {
  if (!memory) { message('note-saved', 'IndexedDB unavailable; note not saved.', 'bad'); return; }
  if (busy) return;
  setBusy(true);
  try {
    localNote = await memory.saveNote($('local-note').value);
    showNote();
  } catch (error) { message('note-saved', 'Save failed: ' + error.message, 'bad'); }
  finally { setBusy(false); }
}
async function exportDevice() {
  if (!memory) { message('device-status', 'Browser storage unavailable. Export disabled.', 'bad'); return; }
  if (busy) return;
  setBusy(true);
  try {
    const data = await memory.exportLocal();
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)],
      {type: 'application/json'}));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'bean-device-memory.json';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    // Revoke after the download is initiated, not before browser consumes it.
    setTimeout(() => URL.revokeObjectURL(url), 1500);
    message('device-status', 'Export created locally. Nothing was sent to GitHub.', 'good');
  } catch (error) { message('device-status', 'Export failed: ' + error.message, 'bad'); }
  finally { setBusy(false); }
}
async function importDevice() {
  const file = $('import-file').files && $('import-file').files[0];
  if (!file || !memory) return;
  if (file.size > 100000) {
    message('device-status', 'Import exceeds 100 KB size limit.', 'bad');
    return;
  }
  if (!confirm('Replace this device’s saved BEAN demo ledger, local note and receipt with the selected backup?')) return;
  setBusy(true);
  try {
    const data = JSON.parse(await file.text());
    ledger = await memory.importLocal(data);
    localNote = await memory.loadNote();
    latestReceipt = (await memory.loadPublicReceipt())?.manifest || null;
    await showLedger();
    showNote();
    message('device-status', 'Verified backup restored to IndexedDB on this device.', 'good');
    if (latestReceipt) renderReceipt(latestReceipt, 'cached', data.public_receipt.verified_at);
  } catch (error) { message('device-status', 'Import rejected: ' + error.message, 'bad'); }
  finally { $('import-file').value = ''; setBusy(false); }
}
async function copyForChat() {
  try {
    // A handoff is explicitly user-initiated and never posted to public GitHub Issues.
    const handoff = {
      schema: 'bean.device.handoff.v1',
      source: 'private browser-local demo cache; not Python Core memory',
      public_checkpoint: latestReceipt ? {
        generation: latestReceipt.generation,
        receipt_sha256: latestReceipt.receipt_sha256
      } : null,
      local_note: $('local-note').value,
      synthetic_patch_count: ledger.patches.length
    };
    await navigator.clipboard.writeText(JSON.stringify(handoff, null, 2));
    message('device-status',
      'Copied device context. Paste only into a private conversation, not a public GitHub issue.',
      'good');
  } catch (error) {
    message('device-status', 'Clipboard unavailable: ' + error.message, 'bad');
  }
}
async function clearDevice() {
  if (!memory || busy) return;
  if (!confirm('Delete this site’s BEAN demo ledger, note and cached public receipt from this device?')) return;
  setBusy(true);
  try {
    await memory.clearAll();
    ledger = await memory.loadLedger();
    localNote = null;
    latestReceipt = null;
    for (const id of ['g', 'b', 'e', 'c', 'source', 'hash', 'previous', 'bytes']) {
      $(id).textContent = '–';
    }
    message('receipt-status', 'Cached public receipt cleared. Use Refresh to retrieve GitHub again.');
    await showLedger();
    showNote();
    message('device-status', 'Browser-local BEAN demo storage cleared. Nothing on GitHub changed.', 'good');
  } catch (error) { message('device-status', 'Clear failed: ' + error.message, 'bad'); }
  finally { setBusy(false); }
}
async function bootstrap() {
  for (const [id, handler] of [
    ['step', doEvent], ['reset', doReset], ['verify', doVerify],
    ['save-note', saveLocalNote], ['export-device', exportDevice],
    ['copy-context', copyForChat], ['clear-device', clearDevice],
    ['refresh', refreshPublicReceipt]
  ]) $(id).addEventListener('click', handler);
  $('import-file').addEventListener('change', importDevice);
  try {
    memory = await DeviceMemory.open();
    ledger = await memory.loadLedger();
    localNote = await memory.loadNote();
    message('device-status', 'IndexedDB active. This device remembers between visits.', 'good');
  } catch (error) {
    if (memory) memory.close();
    memory = null;
    ledger = await freshLedger();
    message('device-status',
      'Browser storage unavailable or invalid: ' + error.message +
      '. Demo runs in temporary session memory; no persistence is claimed.', 'bad');
    for (const id of ['save-note','import-file','export-device','clear-device']) $(id).disabled = true;
  }
  $('storage-status').textContent = memory ? 'Persistent on this device' : 'Session-only, not saved';
  await showLedger();
  showNote();
  await refreshPublicReceipt();
  if ('serviceWorker' in navigator && window.isSecureContext) {
    try {
      await navigator.serviceWorker.register('./sw.js', {scope: './'});
      $('offline-status').textContent = 'Offline app shell available after first successful install.';
    } catch (error) {
      $('offline-status').textContent = 'Offline app shell unavailable: ' + error.message;
    }
  } else {
    $('offline-status').textContent = 'Offline app install requires HTTPS and service worker support.';
  }
}
bootstrap();
