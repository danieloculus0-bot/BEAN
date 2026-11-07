// End-to-end browser test: real Chromium IndexedDB, reload and offline shell.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';
import {sha256} from '../docs/bean-demo/device-memory.mjs';

const origin = 'http://127.0.0.1:9876';
async function waitForServer() {
  for (let i = 0; i < 40; i++) {
    try {
      const response = await fetch(origin + '/bean-demo/');
      if (response.ok) return;
    } catch (_) { /* server startup */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Local demo server did not start');
}
async function manifest() {
  const body = {
    schema: 'bean.github.invoke.v1',
    synthetic_only: true,
    generation: 77,
    boots: 77,
    events: 1000,
    processed_digital_commands: 2,
    source_sha: 'a'.repeat(40),
    databases: {core: {bytes: 2048}}
  };
  body.receipt_sha256 = await sha256(body);
  return body;
}

test('BEAN page persists a note and patch timeline across reload and offline restart', async () => {
  const server = spawn('python3', ['-m', 'http.server', '9876', '--bind', '127.0.0.1', '--directory', 'docs'],
    {stdio: 'ignore'});
  let browser;
  try {
    await waitForServer();
    const payload = await manifest();
    browser = await chromium.launch({headless: true});
    const context = await browser.newContext({serviceWorkers: 'allow'});
    const page = await context.newPage();
    await page.route('https://raw.githubusercontent.com/danieloculus0-bot/BEAN/main/research/github_brain/manifest.json**',
      route => route.fulfill({status: 200, contentType: 'application/json',
        headers: {'access-control-allow-origin': '*'}, body: JSON.stringify(payload)}));
    await page.goto(origin + '/bean-demo/', {waitUntil: 'load'});
    await page.waitForFunction(() => document.getElementById('device-status').textContent.includes('IndexedDB active'));
    await page.waitForFunction(() => document.getElementById('receipt-status').textContent.includes('verified'));
    assert.equal(await page.locator('#g').textContent(), '77');

    await page.locator('#local-note').fill('Remember this on my device, not GitHub.');
    await page.locator('#save-note').click();
    await page.waitForFunction(() => document.getElementById('note-saved').textContent.includes('Saved'));
    await page.locator('#step').click();
    await page.waitForFunction(() => document.getElementById('steps').textContent === '1');
    await page.locator('#step').click();
    await page.waitForFunction(() => document.getElementById('steps').textContent === '2');
    await page.reload();
    await page.waitForFunction(() => document.getElementById('steps').textContent === '2');
    assert.equal(await page.locator('#local-note').inputValue(),
      'Remember this on my device, not GitHub.');
    assert.match(await page.locator('#patch-status').textContent(), /SHA-256 replay verified/);

    // Registration, activation and a controller are prerequisites to offline reload.
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        await new Promise(resolve => navigator.serviceWorker.addEventListener(
          'controllerchange', resolve, {once: true}));
      }
    });
    await page.unrouteAll();
    await context.setOffline(true);
    await page.reload({waitUntil: 'load'});
    await page.waitForFunction(() => document.getElementById('device-status').textContent.includes('IndexedDB active'));
    await page.waitForFunction(() => document.getElementById('receipt-status').textContent.includes('cached verified'));
    assert.equal(await page.locator('#steps').textContent(), '2');
    assert.equal(await page.locator('#g').textContent(), '77');
    assert.equal(await page.locator('#local-note').inputValue(),
      'Remember this on my device, not GitHub.');
    await context.close();
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
});
