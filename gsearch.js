/* gsearch.js — all-in-one search: koi bhi keyword likho (OI, GTI, Radar, X-Ray,
   RELIANCE...) -> feature ya stock ka result. "dum person friendly" (user request). */
(function () {
  /* [keywords, display title, section id] — id "find:" hone par runtime resolve */
  var FEAT = [
    ["oi option chain pcr max pain walls expiry put call", "OI — Option Chain + PCR", "gti"],
    ["greeks theta delta gamma vega option premium calculator", "Greeks Calculator", "find:grQ"],
    ["gti zone manish indicator green", "GTI Zones", "gti"],
    ["xray x ray market xray evening closing analysis", "Market X-Ray (evening)", "dash"],
    ["chart candle pattern level support resistance volume profile alert", "Chart Reading — any stock", "chartread"],
    ["global radar world us market dow nasdaq crude gold dollar fed", "Global Radar", "global"],
    ["screener filter scan rsi breakout 52w", "Screener", "screener"],
    ["heatmap sector map heat sectoral", "Sector Map", "heatmap"],
    ["index indices nifty sensex bank midcap smallcap pe pb", "Indices", "indices"],
    ["fundamental fundamentals pe roe debt", "Fundamentals", "fundamentals"],
    ["company card stock quote profile", "Company Card — search any stock", "company"],
    ["portfolio holdings", "Portfolio", "portfolio"],
    ["futures rollover premium basis", "Futures", "futures"],
    ["news headline digest", "News", "news"],
    ["event calendar result dividend board meeting", "Events", "events"],
    ["ipo gmp listing allotment subscribe grey market", "IPO", "ipo"],
    ["crypto btc eth bitcoin fear greed", "Crypto", "crypto"],
    ["ai forecast timesfm prediction", "AI Forecast", "ai"],
    ["aibrain ai brain mood stocks", "AI Brain", "aibrain"],
    ["filing filings sebi disclosure", "Filings", "filings"],
    ["learn education glossary basics", "Learn", "learn"],
    ["study studies case backtest", "Studies", "studies"],
    ["note notes my notes", "My Notes", "mynotes"],
    ["mf mutual fund nav tracker", "MF Tracker", "mf"],
    ["deepfund deep fund", "Deep Fund", "deepfund"],
    ["dash dashboard home vix fii dii preopen breadth", "Dashboard", "dash"],
    ["alert alarm level cross telegram price", "Price Alerts (Chart Reading me)", "chartread"]
  ];

  for (var f = 0; f < FEAT.length; f++) FEAT[f][0] = FEAT[f][0].split(" ");

  var SYMS = null; /* lazy symbols.json */

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return "&#" + c.charCodeAt(0) + ";";
    });
  }

  function resolveSec(id) {
    var el = null;
    if (id.indexOf("find:") === 0) {
      var t = document.getElementById(id.slice(5));
      if (t) {
        var p = t;
        while (p && p.tagName !== "SECTION") p = p.parentElement;
        if (p) return p.id;
      }
      return "";
    }
    el = document.getElementById(id);
    if (el) return id;
    return "";
  }

  function mount() {
    var home = document.getElementById("home");
    if (!home) return;
    var tag = home.querySelector(".tagline");
    var wrap = document.createElement("div");
    wrap.style.cssText = "position:relative;margin:12px 0 4px";
    wrap.innerHTML =
      '<input id="gq" type="text" placeholder="Search anything — OI, GTI, Radar, X-Ray, RELIANCE..." ' +
      'autocomplete="off" style="width:100%;box-sizing:border-box;padding:10px 14px;border-radius:12px;' +
      'border:1px solid rgba(125,180,255,.5);background:rgba(96,165,250,.1);color:inherit;font-size:14px">' +
      '<div id="gs" style="display:none;position:absolute;top:100%;left:0;right:0;z-index:80;max-height:260px;' +
      'overflow-y:auto;background:#161b26;border:1px solid rgba(125,180,255,.4);border-radius:0 0 12px 12px;' +
      'box-shadow:0 8px 24px rgba(0,0,0,.5)"></div>';
    if (tag && tag.nextSibling) home.insertBefore(wrap, tag.nextSibling);
    else home.insertBefore(wrap, home.firstChild);

    var inp = document.getElementById("gq");
    var box = document.getElementById("gs");

    function draw() {
      var q = inp.value.trim().toLowerCase();
      if (!q) { box.style.display = "none"; return; }
      if (!SYMS) {
        fetch("data/symbols.json").then(function (r) { return r.json(); })
          .then(function (d) { SYMS = d; draw(); }).catch(function () {});
        return;
      }
      var out = "", n = 0;
      var words = q.split(/\s+/);
      for (var i = 0; i < FEAT.length && n < 7; i++) {
        var hit = false;
        for (var w = 0; w < words.length; w++) {
          var qw = words[w];
          var kws = FEAT[i][0];
          for (var x = 0; x < kws.length; x++) {
            if (kws[x] === qw || (qw.length >= 2 && kws[x].slice(0, qw.length) === qw)) { hit = true; break; }
          }
          if (hit) break;
        }
        if (!hit) continue;
        var sec = resolveSec(FEAT[i][2]);
        out += '<div data-gs-sec="' + esc(sec) + '" style="padding:9px 12px;cursor:pointer;' +
          'border-bottom:1px solid rgba(255,255,255,.06);display:flex;justify-content:space-between;gap:8px">' +
          '<b style="font-size:13px">' + esc(FEAT[i][1]) + '</b>' +
          '<span class="note" style="font-size:11px;align-self:center">' + esc(sec) + '</span></div>';
        n++;
      }
      var m = 0;
      var qs = q.toUpperCase();
      var L = SYMS.syms || [];
      for (var j = 0; j < L.length && n < 15 && m < 8; j++) {
        var it = L[j];
        if (it.s.indexOf(qs) === 0 || (it.n || "").toLowerCase().indexOf(q) >= 0) {
          out += '<div data-gs-sym="' + esc(it.s) + '" style="padding:9px 12px;cursor:pointer;' +
            'border-bottom:1px solid rgba(255,255,255,.06);display:flex;justify-content:space-between;gap:8px">' +
            '<b style="font-size:13px">' + esc(it.s) + '</b>' +
            '<span class="note" style="font-size:11px;text-align:right">' + esc(it.n) + ' · chart</span></div>';
          n++; m++;
        }
      }
      if (!out) out = '<div class="note" style="padding:10px 12px">kuch nahi mila — try: gti, oi, xray, radar</div>';
      box.innerHTML = out;
      box.style.display = "block";
    }

    function goStock(sym) {
      box.style.display = "none";
      location.hash = "#chartread";
      setTimeout(function () {
        var ci = document.getElementById("crSearch");
        if (!ci) return;
        ci.value = sym;
        ci.dispatchEvent(new Event("input", { bubbles: true }));
        setTimeout(function () {
          var first = document.querySelector("#crSugg [data-cr-sym]");
          if (first) first.click();
        }, 350);
      }, 500);
    }

    function goSec(sec) {
      box.style.display = "none";
      if (sec) location.hash = "#" + sec;
    }

    inp.addEventListener("input", draw);
    inp.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        var f = box.querySelector("[data-gs-sec], [data-gs-sym]");
        if (f) f.click();
      }
    });
    document.addEventListener("click", function (e) {
      var t = e.target || e.srcElement;
      while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
      if (!t || !t.getAttribute) { box.style.display = "none"; return; }
      var sym = t.getAttribute("data-gs-sym");
      var sec = t.getAttribute("data-gs-sec");
      if (sym) { goStock(sym); return; }
      if (sec !== null && t.hasAttribute && t.hasAttribute("data-gs-sec")) { goSec(sec); return; }
      if (!wrap.contains(t)) box.style.display = "none";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else { mount(); }
})();
