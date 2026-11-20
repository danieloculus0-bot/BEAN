// Public BEAN demo offline shell. No remote GitHub requests are cached here.
// IndexedDB owns the local checkpoint and private, device-only notes.
const CACHE = 'bean-demo-shell-v3';
// Compute the actual service-worker scope rather than assuming GitHub's /BEAN/ prefix.
// This also supports local HTTP servers that mount the same demo at /bean-demo/.
const DEMO_SCOPE = new URL('./', self.registration.scope).pathname;
const SITE_BASE = new URL('../', self.registration.scope).pathname;
const ASSETS = [
  './', './index.html', './device-memory.mjs', './device-ui.mjs',
  './manifest.webmanifest', '../bean-official.webp', '../ecosystem-nav.css?v=20261120'
];
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key.startsWith('bean-demo-shell-') && key !== CACHE)
        .map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === SITE_BASE + 'bean-official.webp' || url.pathname === SITE_BASE + 'ecosystem-nav.css') {
    event.respondWith(caches.match(request).then(found => found || fetch(request)));
    return;
  }
  if (!url.pathname.startsWith(DEMO_SCOPE)) return;
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE).then(cache => cache.put('./index.html', copy)));
        }
        return response;
      }).catch(() => caches.match('./index.html'))
    );
    return;
  }
  // Versioned same-origin static assets only. Never intercept private local data.
  event.respondWith(caches.match(request).then(found => found || fetch(request)));
});
