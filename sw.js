/* Arthasaar — cache killer (demo UI direct) */
self.addEventListener("install", function (e) {
  self.skipWaiting();
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.map(function (k) { return caches.delete(k); }));
  }));
});
self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
/* fetch handler NAHI hai — sab kuch seedha network se, hamesha fresh */
