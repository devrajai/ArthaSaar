#!/usr/bin/env python3
# fix_theme14.py — v13: site polish + auto-load/retry/refresh
# 1) index.html: IPO tile arrow remove + version bumps
# 2) economypulse/newsvolume/news: summary subtitles remove
# 3) oldapp.js: jload 3x retry (backoff) + IPO data local repo se
# 4) themefix.js: eventRadar economy-pulse style (expandable rows) + auto-refresh
#    (market hours me 3 min, warna 15 min)
import pathlib, re

def rep(p, old, new):
    s = pathlib.Path(p).read_text()
    assert old in s, "MISSING in %s: %r" % (p.name, old[:70])
    pathlib.Path(p).write_text(s.replace(old, new, 1))

# ---------- 1) index.html ----------
i = pathlib.Path("index.html")
rep(i, '<span class="t-nm">IPO ↗</span>', '<span class="t-nm">IPO</span>')
rep(i, 'app.js?v=25sep26a55', 'app.js?v=25sep26a62')
rep(i, 'themefix.js?v=25sep26a52', 'themefix.js?v=25sep26a62')

# ---------- 2) subtitles remove ----------
for f, pat in [
    ("economypulse.js", r' <span style="font-size:11px;opacity:\.65">[^<]*</span>'),
    ("newsvolume.js",    r' <span style="font-size:11px;opacity:\.65">[^<]*</span>'),
    ("news.js",          r' <span style="font-size:11px;opacity:\.65">[^<]*</span>'),
]:
    p = pathlib.Path(f)
    s = p.read_text()
    s2 = re.sub(pat, "", s, count=1)
    assert s2 != s, "subtitle not found in " + f
    p.write_text(s2)
    print(f, "subtitle removed")

# ---------- 3) oldapp.js ----------
a = pathlib.Path("oldapp.js")
old = '''function jload(key, url) {
  if (!cache[key]) cache[key] =
    fetch((url || BASE + key + ".json") + "?t=" + Date.now())
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
  return cache[key];
}'''
new = '''function jload(key, url) {
  if (!cache[key]) cache[key] = (function attempt(n) {
    return fetch((url || BASE + key + ".json") + "?t=" + Date.now())
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch((e) => {
        if (n < 3) return new Promise((res) => setTimeout(res, 500 * (n + 1))).then(() => attempt(n + 1));
        delete cache[key];
        throw e;
      });
  })(0);
  return cache[key];
}'''
rep(a, old, new)
rep(a, 'const IPO_URL = "https://raw.githubusercontent.com/devrajai/ipo-terminal/main/data/ipo-data.json";',
       'const IPO_URL = "ipo/data/ipo-data.json"; // v13: local repo data (auto-update hota hai)')

# app.js VER bump
aj = pathlib.Path("app.js")
rep(aj, 's.src = f + "?v=as12";', 's.src = f + "?v=as13";')

# ---------- 4) themefix.js: eventRadar restyle ----------
t = pathlib.Path("themefix.js")
old = '''      var html = "";
      var nOpen = fut.filter(function (e) { return e.type === "OPEN"; }).length;
      html += "<div class='as-fr as-frt'><span>EVENT</span><b>" + nOpen + " open · " + (fut.length - nOpen) + " close</b></div>";
      Object.keys(mk).slice(0, 10).forEach(function (k) {
        html += "<div class='as-evh'><span>" + k + "</span></div>";
        mk[k].forEach(function (e) {
          html += "<div class='as-evr'><span class='as-evb " + String(e.type || "").toLowerCase() + "'>" + e.type + "</span>" +
            "<span class='as-evn'>" + String(e.name || "").replace(/ Limited$| Ltd$/i, "") + "</span></div>";
        });
      });
      if (!fut.length) html += "<div class='as-evm'>koi upcoming event data nahi</div>";
      var card = document.getElementById("evCard");
      if (card) card.innerHTML = html;
    }).catch(function () {});'''
new = '''      var byName = {};
      fetch("ipo/data/ipo-data.json").then(function (r) { return r.json(); }).then(function (id) {
        (id.ipos || []).forEach(function (x) { byName[String(x.name || "").toLowerCase()] = x; });
        render();
      }).catch(function () { render(); });
      function esc2(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
      function row(e) {
        var x = byName[String(e.name || "").toLowerCase()] || {};
        var open = String(e.type || "").toUpperCase() === "OPEN";
        var d = e.date ? e.date.slice(8) + "/" + e.date.slice(5, 7) : "";
        var nm2 = String(e.name || "").replace(/ Limited$| Ltd$/i, "");
        var bits = [];
        if (x.price && x.price !== "\u2014") bits.push("Price " + esc2(x.price));
        if (x.lot && x.lot !== "\u2014") bits.push("Lot " + esc2(x.lot));
        if (x.gmp && x.gmp !== "\u2014") bits.push("GMP " + esc2(x.gmp));
        return '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
          '<b>' + esc2(nm2) + '</b>' +
          '<span style="margin-left:auto;font-weight:700;font-size:11.5px;color:' + (open ? "#77f37b" : "#ff8b8b") + '">' + esc2(e.type || "") + ' \u00b7 ' + d + '</span></summary>' +
          '<div style="padding:6px 14px 10px 14px;font-size:12.5px;opacity:.85;line-height:1.6">' + (bits.join(" \u00b7 ") || "IPO calendar event") + '</div></details>';
      }
      function render() {
        var html = "";
        var nOpen = fut.filter(function (e) { return e.type === "OPEN"; }).length;
        html += "<div class='as-fr as-frt'><span>EVENT RADAR</span><b>" + nOpen + " open · " + (fut.length - nOpen) + " close</b></div>";
        Object.keys(mk).slice(0, 10).forEach(function (k) {
          html += "<div class='as-evh'><span>" + k + "</span></div>";
          mk[k].forEach(function (e) { html += row(e); });
        });
        if (!fut.length) html += "<div class='as-evm'>koi upcoming event data nahi</div>";
        var card = document.getElementById("evCard");
        if (card) card.innerHTML = html;
      }
    }).catch(function () {});'''
rep(t, old, new)

# auto-refresh (market hours 3 min / hamesha 15 min)
old2 = '''  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 2500);
  setTimeout(desk, 6000);
})();'''
new2 = '''  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 2500);
  setTimeout(desk, 6000);
  /* v13: auto-refresh - market hours (Mon-Fri 9:15-15:30 IST) me 3 min, warna 15 min */
  function mktOpen() {
    var n = new Date();
    var ist = new Date(n.getTime() + (330 + n.getTimezoneOffset()) * 60000);
    var m = ist.getHours() * 60 + ist.getMinutes();
    return ist.getDay() >= 1 && ist.getDay() <= 5 && m >= 555 && m <= 930;
  }
  setInterval(function () {
    try { ticker(); desk(); radarHead(); eventRadar(); } catch (e) {}
  }, 900000);
  setInterval(function () {
    if (mktOpen()) { try { ticker(); desk(); radarHead(); eventRadar(); } catch (e) {} }
  }, 180000);
})();'''
rep(t, old2, new2)

print("v13 applied: index, 3 subtitles, jload retry, IPO local, eventRadar cards, auto-refresh")
