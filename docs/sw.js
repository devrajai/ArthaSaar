/* ---------------------------------------------------------------------------
   Self-destructing service worker.

   WHY THIS FILE EXISTS
   The previous ArthaSaar site (a different codebase, now gone) registered a
   service worker at this exact path with scope "/ArthaSaar/". Its fetch handler
   was cache-first and precached "./" and "./index.html", so the browser kept
   serving that OLD app shell from cache and never requested the new files.
   That is why rebuilding the site appeared to change nothing on screen.

   The old worker's script URL had been 404ing (its repo was deleted), so the
   browser could never run an update check. Now that a valid script exists here
   again, the browser will fetch it, notice the bytes changed, and install this
   one - which tears the old cache down and removes itself.

   After this runs once, the site is a normal static page again: no worker, no
   cache, always the current file.

   Browsers revalidate a service worker script on navigation, so this should take
   effect on the first or second reload. To force it immediately: DevTools ->
   Application -> Service Workers -> Unregister, and Clear site data.
--------------------------------------------------------------------------- */

self.addEventListener("install", () => {
  // take over from the old worker immediately, don't wait for tabs to close
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    // 1. drop every cache the old worker created (arthasaar-shell-v3, etc.)
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    } catch (e) { /* ignore */ }

    // 2. remove ourselves, so nothing intercepts requests again
    try { await self.registration.unregister(); } catch (e) { /* ignore */ }

    // 3. reload any open tab so the real page is fetched from the network
    try {
      const clients = await self.clients.matchAll({ type: "window" });
      clients.forEach((c) => { try { c.navigate(c.url); } catch (e) {} });
    } catch (e) { /* ignore */ }
  })());
});

// No fetch handler on purpose: requests fall through to the network untouched,
// so nothing stale can ever be served from this worker.
