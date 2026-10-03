// ArthaSaar free offline cache
const CACHE="arthasaar-shell-v2";
const SHELL=[
  "./",
  "./index.html",
  "./researchpage.js?v=7",
  "./manifest.webmanifest?v=2"
];
self.addEventListener("install",event=>{
  event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener("activate",event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener("fetch",event=>{
  const req=event.request;
  if(req.method!=="GET")return;
  if(req.url.includes("/data/")){
    event.respondWith(fetch(req,{cache:"no-store"}).then(resp=>{
      const copy=resp.clone();caches.open(CACHE).then(c=>c.put(req,copy));return resp;
    }).catch(()=>caches.match(req)));
    return;
  }
  event.respondWith(caches.match(req).then(cached=>cached||fetch(req).then(resp=>{
    const copy=resp.clone();caches.open(CACHE).then(c=>c.put(req,copy));return resp;
  })));
});
