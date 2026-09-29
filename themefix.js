/* themefix.js — NEW UI EDITION (locked v28 design):
   1) 5-THEME LOOK toggle: LIGHT → DARK → AMOLED → GENZ → GENZ DARK (vars newui.css)
   2) 12-hour clock (no IST label)
   3) [data-go] navigation + dock + 3-line nav active states
   4) ALL CARDS menu + search palette + toast
   5) merged sections ke loaders (dash→home, studies+mynotes→learn)
   6) forecast radar (aiHead) + event radar (events) + auto-refresh cycles
   Old chrome (ticker tape, hero panel, calm.css, LIGHT/DARK pill) — REMOVED. */
(function () {
  "use strict";
  if (window.MB_LOCKED) return;

  /* ================= 1) 5-THEME LOOK TOGGLE ================= */
  var T = [["a", "LIGHT"], ["b", "DARK"], ["c", "AMOLED"], ["d", "GENZ"], ["e", "GENZ DARK"]];
  var ti = 1, html = document.documentElement;
  try {
    var sv = localStorage.getItem("as-theme5");
    if (sv) { for (var k = 0; k < T.length; k++) if (T[k][0] === sv) ti = k; }
    else if ((localStorage.getItem("mb-theme") || "") === "light") ti = 0; /* purana light user -> LIGHT */
  } catch (e) {}
  function applyT() {
    html.setAttribute("data-theme", T[ti][0]);
    try { localStorage.setItem("as-theme5", T[ti][0]); } catch (e) {}
  }
  applyT();
  var tb = document.getElementById("themeBtn");
  if (tb) tb.onclick = function () { /* oldapp ka onclick override — last binding jeet-ta hai */
    ti = (ti + 1) % T.length; applyT(); toast(T[ti][1] + " mode");
  };

  /* ================= 2) 12-hour clock ================= */
  function tick12() {
    var d = new Date(), h = d.getHours(), ap = h >= 12 ? "PM" : "AM";
    h = h % 12; if (h === 0) h = 12;
    var c = document.getElementById("clock");
    if (c) c.textContent = [h, d.getMinutes(), d.getSeconds()].map(function (n) {
      return String(n).padStart(2, "0");
    }).join(":") + " " + ap;
  }
  tick12(); setInterval(tick12, 1000);

  /* ================= toast ================= */
  var tEl = null, tTm = null;
  function toast(msg) {
    try {
      if (!tEl) tEl = document.getElementById("asToast");
      if (!tEl) return;
      tEl.textContent = msg;
      tEl.classList.add("show");
      if (tTm) clearTimeout(tTm);
      tTm = setTimeout(function () { tEl.classList.remove("show"); }, 1400);
    } catch (e) {}
  }

  /* ================= 3) [data-go] + dock + nav active ================= */
  document.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest("[data-go]") : null;
    if (b) { location.hash = "#" + b.getAttribute("data-go"); closeOv(); }
  });
  var TOOLS_IDS = { futures: 1, charts: 1, gti: 1, ai: 1, aibrain: 1, internals: 1, tools: 1 };
  function syncChrome() {
    var id = (location.hash || "#home").replace("#", "").split("/")[0] || "home";
    var dH = document.getElementById("dHome"), dL = document.getElementById("dLearn"),
        dG = document.getElementById("dGrid"), dP = document.getElementById("dPort");
    if (dH) dH.classList.toggle("on", id === "home");
    if (dL) dL.classList.toggle("on", id === "learn" || id === "arthabodh" || id === "studies" || id === "mynotes");
    if (dG) dG.classList.toggle("on", !!TOOLS_IDS[id]);
    if (dP) dP.classList.toggle("on", id === "portfolio");
    var btns = document.querySelectorAll(".nav button[data-go]");
    for (var i = 0; i < btns.length; i++) btns[i].classList.toggle("active", btns[i].getAttribute("data-go") === id);
  }
  window.addEventListener("hashchange", syncChrome);
  syncChrome();

  /* ================= 4) menu + palette ================= */
  var CARDS = [
    ["home", "Home", "aapka hub"],
    ["dash", "Market X-Ray", "preopen · movers"],
    ["company", "Company Card", "search any stock"],
    ["indices", "Indices", "139 tracked"],
    ["heatmap", "Sector Map", "today by sector"],
    ["screener", "Screener", "2,085 stocks"],
    ["fundamentals", "Fundamentals", "PE ROE debt"],
    ["mf", "MF Tracker", "nav sip funds"],
    ["deepfund", "Deep Fund", "screener.in weekly"],
    ["filings", "Filings", "company results"],
    ["futures", "Futures", "F&O chains"],
    ["charts", "Charts", "TradingView live"],
    ["gti", "GTI Zones", "demand supply POC"],
    ["ai", "AI Forecast", "TimesFM 21-day"],
    ["aibrain", "AI Brain", "mood crash report"],
    ["internals", "Market Internals", "breadth TRIN McClellan"],
    ["crypto", "Crypto", "top 100 coins"],
    ["global", "Global", "US gold crude"],
    ["news", "News", "India market"],
    ["events", "Events", "GDP jobs RBI"],
    ["ipo", "IPO", "terminal GMP listing"],
    ["portfolio", "Portfolio", "holdings P/L"],
    ["arthabodh", "ArthaBodh", "school · studies · notes"]
  ];
  function buildMenu() {
    var ml = document.getElementById("menuList");
    if (!ml) return;
    var h = "";
    CARDS.forEach(function (c) {
      h += '<button class="mb" data-go="' + c[0] + '"><span>' + c[1] + '</span><small>' + c[2] + '</small></button>';
    });
    ml.innerHTML = h;
  }
  function closeOv() {
    var m = document.getElementById("moreOv"), p = document.getElementById("palOv");
    if (m) m.classList.remove("open");
    if (p) p.classList.remove("open");
  }
  function wireOverlays() {
    var m = document.getElementById("moreOv"), p = document.getElementById("palOv");
    var dm = document.getElementById("dMore"), ds = document.getElementById("dSearch"), mx = document.getElementById("mx");
    if (dm) dm.addEventListener("click", function () { if (m) m.classList.add("open"); });
    if (ds) ds.addEventListener("click", function () {
      if (p) p.classList.add("open");
      var q = document.getElementById("palQ");
      if (q) setTimeout(function () { q.focus(); }, 40);
    });
    if (mx) mx.addEventListener("click", closeOv);
    if (m) m.addEventListener("click", function (e) { if (e.target === m) closeOv(); });
    if (p) p.addEventListener("click", function (e) { if (e.target === p) closeOv(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeOv();
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        if (p) { p.classList.add("open"); var q = document.getElementById("palQ"); if (q) setTimeout(function () { q.focus(); }, 40); }
      }
    });
    var q = document.getElementById("palQ");
    if (q) q.addEventListener("input", function () {
      var v = q.value.toLowerCase(), out = "";
      CARDS.forEach(function (c) {
        if (!v || (c[0] + " " + c[1] + " " + c[2]).toLowerCase().indexOf(v) !== -1)
          out += '<button class="mb" data-go="' + c[0] + '"><span>' + c[1] + '</span><small>' + c[2] + '</small></button>';
      });
      var pl = document.getElementById("palList");
      if (pl) pl.innerHTML = out || '<div class="note">kuch nahi mila</div>';
    });
  }

  /* dash boxes ab #home (TODAY) me hain — dash loader manually boot pe chalao
     (learn/studies/mynotes arthabodh.js khud merge karta hai — #arthabodh) */
  function bootMerged() {
    try { if (typeof loaders !== "undefined" && loaders.dash) loaders.dash(); } catch (e) {}
  }

  /* ================= 6) forecast radar + event radar (data, old UI se carry) ================= */
  var fmem = {};
  function fjson(url, cb, n) {
    var m = fmem[url], now = Date.now();
    if (m && now - m.t < 600000) { cb(m.d); return; }
    fetch(url).then(function (r) { return r.json(); }).then(function (d) {
      fmem[url] = { t: now, d: d }; cb(d);
    }).catch(function () {
      n = (n || 0) + 1;
      if (n <= 4) setTimeout(function () { fjson(url, cb, n); }, 3000 * n);
    });
  }
  function esc(s) { if (s == null) s = ""; return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function radarHead() {
    fjson("data/timesfm_forecasts.json", function (d) {
      var el = document.getElementById("aiHead");
      if (!el || !d || !d.forecasts) return;
      var by = {};
      (d.forecasts || []).forEach(function (f) { by[f.name] = f; });
      var want = ["Nifty 50", "Bank Nifty", "Sensex", "Nifty IT", "India VIX", "Gold (COMEX)", "Bitcoin", "Ethereum", "USD-INR"];
      var rows = "";
      want.forEach(function (w) {
        var f = by[w];
        if (!f) return;
        var c = Number(f.median_chg_pct) || 0;
        var up = f.direction === "up" || c > 0;
        rows += "<div class='as-fr'><span>" + w + "</span><b class='" + (up ? "u" : "d") + "'>" +
          (c >= 0 ? "+" : "") + c.toFixed(1) + "% 21d" +
          (f.direction === "up" ? " ▲" : f.direction === "down" ? " ▼" : " ●") + "</b></div>";
      });
      var F = d.forecasts || [];
      var nUp = F.filter(function (f) { return f.direction === "up"; }).length;
      el.innerHTML = "<div class='as-fr as-frt'><span>FORECAST RADAR</span><b>" +
        nUp + "▲ " + (F.length - nUp) + "▼</b></div>" + rows;
    });
  }
  function watchAIHead() {
    var el = document.getElementById("aiHead");
    if (!el) return;
    radarHead();
    var busy = false;
    var ob = new MutationObserver(function () {
      if (busy) return;
      if (el.innerHTML.indexOf("FORECAST RADAR") === -1) {
        busy = true;
        setTimeout(function () { busy = false; }, 800);
        radarHead();
      }
    });
    ob.observe(el, { childList: true, subtree: true });
  }

  var evOpenState = {};
  function eventRadar() {
    fjson("ipo/data/terminal-events.json", function (d) {
      var evs = (d && d.events) || [];
      var today = new Date();
      function iso(dt) { return dt.toISOString().slice(0, 10); }
      var t = iso(today);
      var fut = evs.filter(function (e) { return e.date >= t; })
                   .sort(function (a, b) { return a.date < b.date ? -1 : 1; });
      var mk = {};
      fut.forEach(function (e) {
        var k = e.date === t ? "AAJ" : e.date === iso(new Date(today.getTime() + 864e5)) ? "KAL" : e.date.slice(8) + "/" + e.date.slice(5, 7);
        (mk[k] = mk[k] || []).push(e);
      });
      var byName = {};
      fjson("ipo/data/ipo-data.json", function (id) {
        (id.ipos || []).forEach(function (x) { byName[String(x.name || "").toLowerCase()] = x; });
        render();
      });
      function ok(v) { return v != null && v !== "" && v !== "—"; }
      function row(e) {
        var x = byName[String(e.name || "").toLowerCase()] || {};
        var open = String(e.type || "").toUpperCase() === "OPEN";
        var d = e.date ? e.date.slice(8) + "/" + e.date.slice(5, 7) : "";
        var nm2 = String(e.name || "").replace(/ Limited$| Ltd$/i, "");
        var bits = [];
        if (ok(x.type)) bits.push(esc(x.type));
        if (ok(x.status)) bits.push("Status: " + esc(x.status));
        if (ok(x.price)) bits.push("Price " + esc(x.price));
        if (ok(x.lot)) bits.push("Lot " + esc(x.lot));
        if (ok(x.size)) bits.push("Size " + esc(x.size));
        if (ok(x.open) || ok(x.close)) bits.push("Dates " + esc(ok(x.open) ? x.open : "—") + " → " + esc(ok(x.close) ? x.close : "—"));
        if (ok(x.listing)) bits.push("Listing " + esc(x.listing));
        if (ok(x.sub)) bits.push("Sub " + esc(x.sub));
        if (ok(x.gmp)) bits.push("GMP " + esc(x.gmp));
        return '<details data-ev="' + esc(nm2) + '"' + (evOpenState[nm2] ? ' open' : '') + ' style="margin-top:6px">' +
          '<summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:9px;background:var(--glass2);border:1px solid var(--border);font-size:13.5px;flex-wrap:wrap;list-style:none">' +
          '<b>' + esc(nm2) + '</b>' +
          '<span style="margin-left:auto;font-weight:700;font-size:11.5px;color:' + (open ? "var(--up)" : "var(--down)") + '">' + esc(e.type || "") + ' · ' + d + '</span>' +
          '<span class="as-chev">▸</span></summary>' +
          '<div style="padding:6px 14px 10px 14px;font-size:12.5px;opacity:.85;line-height:1.6">' + (bits.join(" · ") || "IPO calendar event") + '</div></details>';
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
        if (card) {
          card.innerHTML = html;
          var ds = card.querySelectorAll("details[data-ev]");
          for (var i = 0; i < ds.length; i++) {
            (function (dd) {
              dd.addEventListener("toggle", function () { evOpenState[dd.getAttribute("data-ev")] = dd.open; });
            })(ds[i]);
          }
        }
      }
    });
  }
  function buildEvents() {
    if (!document.getElementById("evCard")) {
      var sec = document.querySelector("section#events");
      if (sec) {
        var h2 = sec.querySelector("h2");
        var card = document.createElement("div");
        card.className = "card";
        card.id = "evCard";
        if (h2 && h2.nextSibling) sec.insertBefore(card, h2.nextSibling);
        else sec.appendChild(card);
      }
    }
    eventRadar();
  }

  function wireDock() {
    function bind(id, target) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("click", function () { location.hash = "#" + target; });
    }
    bind("dHome", "home");
    bind("dLearn", "learn"); /* arthabodh.js #learn -> #arthabodh merge handle karta hai */
    bind("dGrid", "tools");
    bind("dPort", "portfolio");
  }

  /* ================= boot ================= */
  function boot() {
    buildMenu();
    wireOverlays();
    wireDock();
    bootMerged();
    watchAIHead();
    buildEvents();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 2500);

  /* auto-refresh: market hours (Mon-Fri 9:15-15:30 IST) me 3 min, warna 15 min */
  function mktOpen() {
    var n = new Date();
    var ist = new Date(n.getTime() + (330 + n.getTimezoneOffset()) * 60000);
    var m = ist.getHours() * 60 + ist.getMinutes();
    return ist.getDay() >= 1 && ist.getDay() <= 5 && m >= 555 && m <= 930;
  }
  function cycleLight() { try { radarHead(); eventRadar(); } catch (e) {} }
  function cycleFull() {
    try { fmem = {}; if (window.__MB_FLUSH) window.__MB_FLUSH(); if (window.__MB_RERENDER) window.__MB_RERENDER(); } catch (e) {}
    cycleLight();
  }
  setInterval(cycleFull, 900000);
  setInterval(function () { if (mktOpen()) cycleLight(); }, 180000);
})();
