#!/usr/bin/env python3
"""fix_pwa.py - PWA: manifest + service worker + icons (PIL) + index.html tags. No push notifications."""
from PIL import Image, ImageDraw, ImageFont

def make_icon(size):
    img = Image.new("RGB", (size, size), (7, 12, 23))
    d = ImageDraw.Draw(img)
    m = int(size * 0.06)
    d.rounded_rectangle([m, m, size - m, size - m], radius=int(size * 0.18), outline=(240, 180, 41), width=max(2, size // 64))
    pts = [(int(size*.2), int(size*.66)), (int(size*.38), int(size*.5)), (int(size*.52), int(size*.58)), (int(size*.78), int(size*.3))]
    lw = max(3, size // 40)
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i+1]], fill=(119, 243, 123), width=lw)
    ax, ay = pts[-1]
    d.polygon([(ax, ay - int(size*.06)), (ax + int(size*.09), ay + int(size*.01)), (ax - int(size*.03), ay + int(size*.03))], fill=(119, 243, 123))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.24))
    except Exception:
        f = ImageFont.load_default()
    d.text((size // 2, int(size * 0.82)), "MB", font=f, fill=(240, 180, 41), anchor="mm")
    return img

MANIFEST = '{"name":"Market Brain","short_name":"Market Brain","start_url":"./","scope":"./","display":"standalone","background_color":"#070c17","theme_color":"#070c17","description":"Market intelligence terminal - Indian markets, GTI, OI, AI forecasts","icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]}'

SW = ('var C="mb-v1";'
'self.addEventListener("install",function(e){self.skipWaiting();e.waitUntil(caches.open(C).then(function(c){return c.addAll(["./","./style.css","./app.js","./manifest.json","./icon-192.png"]);}));});'
'self.addEventListener("activate",function(e){e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==C;}).map(function(k){return caches.delete(k);}));}).then(function(){return self.clients.claim();}));});'
'self.addEventListener("fetch",function(e){if(e.request.method!=="GET")return;var u=new URL(e.request.url);if(u.pathname.indexOf("/data/")>=0)return;e.respondWith(fetch(e.request).then(function(r){var cp=r.clone();caches.open(C).then(function(c){c.put(e.request,cp);});return r;}).catch(function(){return caches.match(e.request);}));});')

def main():
    for s in (192, 512):
        make_icon(s).save("icon-%d.png" % s)
    print("icons written")
    open("manifest.json", "w").write(MANIFEST)
    open("sw.js", "w").write(SW)
    print("manifest.json + sw.js written")
    idx = open("index.html", encoding="utf-8").read()
    changed = False
    if 'rel="manifest"' not in idx:
        add = ('<meta name="theme-color" content="#070c17">\n'
               '<link rel="manifest" href="manifest.json">\n'
               '<link rel="apple-touch-icon" href="icon-192.png">\n')
        idx = idx.replace("</head>", add + "</head>"); changed = True
    if "serviceWorker" not in idx:
        swreg = '<script>if("serviceWorker" in navigator){window.addEventListener("load",function(){navigator.serviceWorker.register("sw.js").catch(function(){});});}</script>\n'
        idx = idx.replace("</body>", swreg + "</body>"); changed = True
    if changed:
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: PWA tags added")
    else:
        print("index.html: PWA tags already present")

if __name__ == "__main__":
    main()
