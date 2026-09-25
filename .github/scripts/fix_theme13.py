#!/usr/bin/env python3
# fix_theme13.py — v12: script load reliability (flaky mobile network fix)
# 1) app.js: stable ?v= URLs (browser+SW cache works) + 4 retries with backoff
# 2) index.html: app.js tag bump
# 3) ipo/index.html: 6 script tags -> sequential loader with retry
import pathlib

def rep(p, old, new, cnt=1):
    s = p.read_text()
    assert old in s, "MISSING in %s: %r" % (p.name, old[:70])
    p.write_text(s.replace(old, new, cnt))

# ---------- 1) app.js ----------
a = pathlib.Path("app.js")
rep(a, 's.src = f + "?t=" + Date.now();', 's.src = f + "?v=as12";')
rep(a, '      if (tries[f] <= 2) { i--; setTimeout(next, 500); return; }',
       '      if (tries[f] <= 4) { i--; setTimeout(next, 400 * tries[f]); return; }')
rep(a, '/* ARTHASAAR loader — pulls in the app in strict order (v=i: retry + skip on error, mf renamed mft).',
       '/* ARTHASAAR loader — v12: stable ?v= URLs (cache-friendly) + 4 retries with backoff.')

# ---------- 2) index.html ----------
i = pathlib.Path("index.html")
rep(i, 'app.js?v=25sep26a43', 'app.js?v=25sep26a55')

# ---------- 3) ipo/index.html: retry loader ----------
ip = pathlib.Path("ipo/index.html")
OLD = ('<script src="scripts/ipo-detection.js"></script><script src="scripts/ipo-forecast.js"></script>\n'
       '<script src="scripts/ipo-coach.js"></script>\n'
       '<script src="scripts/ipo-sparkline.js"></script>\n'
       '<script src="scripts/ipo-protools.js"></script><script src="scripts/merge-tools.js"></script>')
NEW = ('<script>\n'
       '/* v12: sequential loader with retry (flaky mobile networks ke liye) */\n'
       '(function () {\n'
       '  var files = ["scripts/ipo-detection.js", "scripts/ipo-forecast.js", "scripts/ipo-coach.js",\n'
       '    "scripts/ipo-sparkline.js", "scripts/ipo-protools.js", "scripts/merge-tools.js"];\n'
       '  var i = 0, tries = {};\n'
       '  function next() {\n'
       '    if (i >= files.length) return;\n'
       '    var f = files[i++];\n'
       '    var s = document.createElement("script");\n'
       '    s.src = f;\n'
       '    s.onload = function () { tries[f] = 0; next(); };\n'
       '    s.onerror = function () {\n'
       '      tries[f] = (tries[f] || 0) + 1;\n'
       '      if (tries[f] <= 4) { i--; setTimeout(next, 400 * tries[f]); return; }\n'
       '      next();\n'
       '    };\n'
       '    document.head.appendChild(s);\n'
       '  }\n'
       '  next();\n'
       '})();\n'
       '</script>')
rep(ip, OLD, NEW)

print("v12 applied | app.js:", "as12" in a.read_text(),
      "| index:", "a55" in i.read_text(),
      "| ipo loader:", "tries[f] <= 4" in ip.read_text())
