// ArthaSaar: old service worker retired. This one unregisters itself and clears caches,
// so visitors stop getting the previous cached site.
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil((async function () {
    try { var keys = await caches.keys(); await Promise.all(keys.map(function (k) { return caches.delete(k); })); } catch (err) {}
    try { await self.registration.unregister(); } catch (err) {}
    try { var cs = await self.clients.matchAll({ type: 'window' }); cs.forEach(function (c) { try { c.navigate(c.url); } catch (e) {} }); } catch (err) {}
  })());
});
