// Public BEAN demo offline shell. No remote GitHub requests are cached here.
// IndexedDB owns the local checkpoint and private, device-only notes.
const CACHE = 'bean-demo-shell-v1';
const ASSETS = [
  './', './index.html', './device-memory.mjs', './device-ui.mjs',
  './manifest.webmanifest', '../bean-official.webp'
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
  if (url.origin !== self.location.origin || !url.pathname.startsWith('/BEAN/bean-demo/')) return;
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
