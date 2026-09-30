/* crtime.js v1 \u2014 full candle-time row + ranges, NO page reloads.
   - intraday chips (chartread.js): 1m 3m 5m 10m 15m 30m 1h 4h 6h 8h
   - range chips (this file): 1D | 1M \u00b7 1Y \u00b7 5Y \u00b7 MAX \u2014 daily archive, clipped at fetch
   - data: jsDelivr CDN (devrajai/arthasaar-data) \u2014 Release assets pe CORS nahi hota
   - range switch = clear cache + re-render in place. location.reload() KABHI nahi
   - 27 Sepb: range chip sirf iv==1d pe highlight (ek hi selected dikhe)
     => landing-page redirect bug khatam. State localStorage (crrange) me. */
(function () {
  "use strict";
  var CDN = "/api/data?ref=data&p=data/";
  var RELRE = /https:\/\/github\.com\/devrajai\/ArthaSaar\/releases\/download\/candles\//;

  /* range: bars to keep (0 = full file). MAX additionally switches daily- -> full- */
  var RANGES = [["1M", "1 mahina", 26], ["1Y", "1 saal", 252], ["5Y", "5 saal", 0], ["MAX", "listing se full history", 0]];
  var RLBL = { "1M": "1D \u00b7 1M (1 mahina)", "1Y": "1D \u00b7 1Y (1 saal)", "5Y": "1D \u00b7 5Y (5 saal)", "MAX": "1D \u00b7 MAX (listing se)" };
  var range = "5Y";

  try {
    var r0 = (window.localStorage.getItem("crrange") || "5y").toUpperCase();
    if (RLBL[r0]) range = r0;
    window.localStorage.setItem("crrange", range.toLowerCase());
    window.sessionStorage.removeItem("crmax");  /* purge old toggle keys */
    window.sessionStorage.removeItem("crgo");
  } catch (e) {}

  function barsOf(b, n) {
    if (!b || !b.t) return b;
    var L = b.t.length;
    if (n > 0 && L > n) {
      b.t = b.t.slice(L - n); b.o = b.o.slice(L - n); b.h = b.h.slice(L - n);
      b.l = b.l.slice(L - n); b.c = b.c.slice(L - n);
      if (b.v) b.v = b.v.slice(L - n);
    }
    return b;
  }
  function clipChunk(d, n) {
    var syms = d && d.syms;
    if (!syms) return d;
    for (var k in syms) barsOf(syms[k], n);
    return d;
  }

  /* ---------- data layer: fetch wrapper ---------- */
  var realFetch = window.fetch;
  if (typeof realFetch === "function") {
    window.fetch = function (u, o) {
      if (typeof u === "string" && RELRE.test(u)) {
        var fu = u.replace(RELRE, CDN);
        var isDaily = fu.indexOf("/daily-") >= 0;
        if (range === "MAX" && isDaily) fu = fu.replace("/daily-", "/full-");
        else if (range !== "MAX" && !isDaily) fu = fu.replace("/full-", "/daily-");
        var n = range === "1M" ? 26 : range === "1Y" ? 252 : 0;
        if (!n) return realFetch.call(window, fu, o);
        return realFetch.call(window, fu, o).then(function (r) {
          if (!r.ok) return r;
          return r.json().then(function (d) {
            try { clipChunk(d, n); } catch (e2) {}
            return new Response(JSON.stringify(d), { status: 200, headers: { "Content-Type": "application/json" } });
          }, function () { return r; });
        });
      }
      return realFetch.call(window, u, o);
    };
  }

  /* ---------- range chips UI ---------- */
  function markActive() {
    var iv = null;
    try { iv = window.__CR__.getCur().iv; } catch (e) {}
    var bs = document.querySelectorAll("[data-crrange]");
    for (var i = 0; i < bs.length; i++)
      bs[i].className = "chip" +
        (iv === "1d" && bs[i].getAttribute("data-crrange") === range ? " on" : "");
  }
  function addChips() {
    var ivs = document.getElementById("crIvs");
    if (!ivs) return;
    if (document.getElementById("crRangeWrap")) { markActive(); return; }
    var wrap = document.createElement("span");
    wrap.id = "crRangeWrap";
    wrap.style.cssText = "display:inline-flex;gap:6px;margin-left:8px;padding-left:8px;border-left:1px solid rgba(125,180,255,.35)";
    for (var i = 0; i < RANGES.length; i++) {
      var b = document.createElement("button");
      b.className = "chip";
      b.setAttribute("data-crrange", RANGES[i][0]);
      b.textContent = RANGES[i][0] === "1M" ? "1MO" : RANGES[i][0];
      b.title = "daily candles \u2014 " + RANGES[i][1];
      wrap.appendChild(b);
    }
    ivs.appendChild(wrap);
    markActive();
  }

  /* ---------- click: switch range in place (no reload) ---------- */
  document.addEventListener("click", function (e) {
    var t = e.target || e.srcElement;
    while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
    if (!t || !t.getAttribute) return;
    var rg = t.getAttribute("data-crrange");
    if (!rg || !RLBL[rg]) return;
    var CR = window.__CR__;
    if (rg === range) {
      if (CR) { try { CR.setIv("1d"); CR.render(); } catch (e2) {} }
      markActive(); return;
    }
    range = rg;
    try { window.localStorage.setItem("crrange", range.toLowerCase()); } catch (e2) {}
    if (CR) {
      try { CR.clearCache(); } catch (e2) {}
      try { CR.setIv("1d"); CR.render(); } catch (e2) {}
    }
    markActive();
  }, false);

  /* ---------- header label (range aware) ---------- */
  function relabel() {
    var CR = window.__CR__, iv = null, sym = "";
    try { var c = CR.getCur(); iv = c.iv; sym = c.sym; } catch (e) {}
    var h = document.querySelector("#crPrice .subhead");
    if (!h) return;
    if (iv !== "1d") return;
    var want = sym + " \u00b7 " + RLBL[range];
    if (h.textContent.indexOf("1D") >= 0 && h.textContent !== want) h.textContent = want;
    var loadNote = document.querySelector("#crPrice .note");
    if (loadNote && loadNote.textContent.indexOf("5-saal daily archive load") >= 0)
      loadNote.textContent = "daily archive (" + RLBL[range] + ") load ho raha...";
  }

  /* ---------- mount + guards ---------- */
  function mount() {
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      var ivs = document.getElementById("crIvs");
      if (ivs) {
        clearInterval(t);
        addChips();
        try {
          new MutationObserver(function () { addChips(); relabel(); })
            .observe(ivs, { childList: true, subtree: true });
        } catch (e) {}
      }
      if (tries > 80) clearInterval(t);
    }, 300);
    setInterval(function () { addChips(); relabel(); }, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else { mount(); }
})();