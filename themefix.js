/* themefix.js v10 - ARTHASAAR PREMIUM (reference header + radars, event tile on top, no small words):
   1) calm.css inject  2) infinity logo  3) favicon fix  4) ARtha-SAAR brand
   5) LIGHT/DARK pill button  6) gradient rline
   7) ticker tape (points + %)  8) hero NIFTY panel (+SENSEX, points)
   9) forecast radar (replaces AI head card)  10) event radar on top of events section */
(function () {
  "use strict";

  /* ---------- 1) calm.css ---------- */
  try {
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = "calm.css?t=" + Date.now();
    document.head.appendChild(l);
  } catch (e) {}

  /* ---------- logo SVGs (infinity — reference design) ---------- */
  var GDEF = "<defs><linearGradient id='asg' x1='0' y1='0' x2='1' y2='1'>" +
    "<stop offset='0' stop-color='#7cc4ff'/><stop offset='1' stop-color='#7ce3a8'/></linearGradient></defs>";
  var INFPATH = "M32 32c-5-8-11-11-16-11C9 21 4 26 4 32s5 11 12 11c5 0 11-3 16-11z" +
    "m0 0c5 8 11 11 16 11 7 0 12-5 12-11s-5-11-12-11c-5 0-11 3-16 11z";
  var LOGO = "<svg viewBox='0 0 64 64' fill='none' xmlns='http://www.w3.org/2000/svg'>" + GDEF +
    "<path d='" + INFPATH + "' stroke='url(#asg)' stroke-width='3.4' stroke-linecap='round'/>" +
    "<circle cx='10' cy='17' r='1.6' fill='#7cc4ff'/><circle cx='54' cy='47' r='1.6' fill='#7ce3a8'/>" +
    "<path d='M20 44l6-6m4-4l6-6' stroke='url(#asg)' stroke-width='1.4' stroke-linecap='round' opacity='.5'/>" +
    "</svg>";
  var FAV = "<svg viewBox='0 0 64 64' fill='none' xmlns='http://www.w3.org/2000/svg'>" + GDEF +
    "<path d='" + INFPATH + "' stroke='url(#asg)' stroke-width='4' stroke-linecap='round'/>" +
    "</svg>";

  /* ---------- apply header ---------- */
  function apply() {
    try {
      var lg = document.querySelector("header .logo");
      if (lg) { lg.innerHTML = LOGO; lg.removeAttribute("style"); }
    } catch (e) {}
    try {
      var fav = document.querySelector("link[rel='icon']");
      if (fav) fav.href = "data:image/svg+xml," + encodeURIComponent(FAV);
    } catch (e) {}
    try {
      var h1 = document.querySelector("header h1");
      if (h1 && h1.innerHTML.indexOf("ARtha") === -1) h1.innerHTML = "ARtha<em>SAAR</em>";
    } catch (e) {}
    try {
      var gl = document.querySelector(".glogo");
      if (gl) gl.textContent = "AS";
    } catch (e) {}
    try {
      var tg = document.querySelector("header .tagline");
      if (tg) tg.style.display = "none";
    } catch (e) {}
    /* gradient rline under header (reference) + ticker tape */
    try {
      var hr = document.querySelector("header");
      if (hr && hr.parentNode) {
        if (!document.querySelector(".as-rline")) {
          var ln = document.createElement("div");
          ln.className = "as-rline";
          hr.parentNode.insertBefore(ln, hr.nextSibling);
        }
        if (!document.querySelector(".as-tape")) {
          var tp = document.createElement("div");
          tp.className = "as-tape";
          tp.innerHTML = "<div class='as-tape-in'><b>ARTHASAAR</b>&nbsp;<span class='t'>market ka saar · shanti se dekho</span></div>";
          hr.parentNode.insertBefore(tp, (document.querySelector(".as-rline") || hr).nextSibling);
        }
      }
    } catch (e) {}
    /* LIGHT/DARK pill */
    try {
      var tb = document.querySelector("#themeBtn");
      if (tb) {
        var sync = function () {
          var light = document.documentElement.getAttribute("data-theme") === "light";
          tb.textContent = light ? "◑ DARK" : "◐ LIGHT";
        };
        sync();
        if (!window.__AS_THEME_OBS) {
          window.__AS_THEME_OBS = new MutationObserver(sync);
          window.__AS_THEME_OBS.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
        }
      }
    } catch (e) {}
  }

  /* ---------- v14: fetch + auto-retry + 10-min memo (fail hote hi khud dobara, duplicate fetch nahi) ---------- */
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

  /* ---------- SENSEX from global.json (yahoo ^BSESN) ---------- */
  function sensex(cb) {
    fjson("data/global.json", function (d) {
      if (!d || !d.items) return cb(null);
      for (var k = 0; k < d.items.length; k++) {
        if (String(d.items[k].name || "").toUpperCase().indexOf("SENSEX") !== -1) return cb(d.items[k]);
      }
      cb(null);
    });
  }

  /* ---------- ticker tape (points + %) ---------- */
  function ticker() {
    fjson("data/indices-all.json", function (d) {
      var tp = document.querySelector(".as-tape");
      if (!tp || !d || !d.indices || !d.indices.length) return;
      var want = ["NIFTY 50", "NIFTY BANK", "SENSEX", "INDIA VIX", "NIFTY IT", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY AUTO", "NIFTY METAL", "NIFTY FMCG"];
      var by = {};
      d.indices.forEach(function (i) { by[i.index] = i; });
      var parts = [];
      want.forEach(function (w) {
        var i = by[w];
        if (!i) return;
        var c = (i.change_pct || 0) > 0 ? "u" : "d";
        var pt = (i.change != null && isFinite(Number(i.change))) ? (Number(i.change) > 0 ? "+" : "") + Number(i.change).toFixed(0) + " · " : "";
        var v = pt + (i.change_pct > 0 ? "+" : "") + (Number(i.change_pct) || 0).toFixed(2) + "%";
        parts.push("<span><b>" + w + "</b> " + Number(i.price).toLocaleString("en-IN") + " <span class='t " + c + "'>" + v + "</span></span>");
      });
      if (parts.length < 4) d.indices.slice(0, 8).forEach(function (i) {
        var c = (i.change_pct || 0) > 0 ? "u" : "d";
        var pt = (i.change != null && isFinite(Number(i.change))) ? (Number(i.change) > 0 ? "+" : "") + Number(i.change).toFixed(0) + " · " : "";
        parts.push("<span><b>" + i.index + "</b> " + Number(i.price).toLocaleString("en-IN") + " <span class='t " + c + "'>" + pt + (i.change_pct > 0 ? "+" : "") + (Number(i.change_pct) || 0).toFixed(2) + "%</span></span>");
      });
      var one = parts.join("");
      var draw = function (sx) {
        if (sx) {
          var c2 = (sx.chg_pct || 0) > 0 ? "u" : "d";
          var sv = (sx.chg_pct > 0 ? "+" : "") + Number(sx.chg_pct).toFixed(2) + "%";
          var spc2 = sx.chg_pct ? sx.price / (1 + sx.chg_pct / 100) : null;
          var spt = spc2 ? (sx.chg_pct > 0 ? "+" : "") + (sx.price - spc2).toFixed(0) + " · " : "";
          var sSpan = "<span><b>SENSEX</b> " + Number(sx.price).toLocaleString("en-IN") + " <span class='t " + c2 + "'>" + spt + sv + "</span></span>";
          one = sSpan + one;
        }
        tp.innerHTML = "<div class='as-tape-in'>" + one + one + "</div>";
      };
      sensex(draw);
    });
  }

  /* ---------- hero NIFTY panel (home top) — points + % ---------- */
  function desk() {
    fjson("data/indices-all.json", function (d) {
      if (!d || !d.indices || !d.indices.length) return;
      var home = document.querySelector("section#home");
      if (!home) return;
      var old = document.querySelector(".as-hero");
      if (old && old.parentNode) old.parentNode.removeChild(old);
      var idx = d.indices;
      var pos = 0;
      idx.forEach(function (i) { if ((i.change_pct || 0) > 0) pos++; });
      var by = {};
      idx.forEach(function (i) { by[i.index] = i; });
      var n = by["NIFTY 50"] || idx[0];
      var v = by["INDIA VIX"];
      var chg = n ? (Number(n.change_pct) || 0) : 0;
      var el = document.createElement("div");
      el.className = "as-hero";
      var dt = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).toUpperCase();
      el.innerHTML = "<div class='as-ht'><span>NIFTY 50 · LIVE</span><span>" + dt + " IST</span></div>" +
        "<div class='as-hv'>" + (n ? Number(n.price).toLocaleString("en-IN") : "—") +
        "<span class='" + (chg >= 0 ? "u" : "d") + "'>" + (chg >= 0 ? "▲" : "▼") + " " + (n && n.change != null && isFinite(Number(n.change)) ? (chg >= 0 ? "+" : "−") + Math.abs(Number(n.change)).toFixed(1) + " pts (" + Math.abs(chg).toFixed(2) + "%)" : Math.abs(chg).toFixed(2) + "%") + "</span></div>" +
        "<div class='as-hg'>" +
        "<div class='as-hc'><i>TREND</i><b class='" + (chg >= 0 ? "u" : "d") + "'>" + (chg >= 0 ? "UP" : "DOWN") + "</b></div>" +
        "<div class='as-hc'><i>BREADTH</i><b class='" + (pos > idx.length / 2 ? "u" : "d") + "'>" + pos + "/" + idx.length + "</b></div>" +
        "<div class='as-hc'><i>SENSEX</i><b id='as-sx'>—</b></div>" +
        "<div class='as-hc'><i>VIX</i><b class='" + (v && (Number(v.change_pct) || 0) < 0 ? "u" : "d") + "'>" + (v ? Number(v.price).toFixed(1) : "—") + "</b></div>" +
        "</div>";
      home.insertBefore(el, home.firstChild);
      sensex(function (sx) {
        var cell = document.getElementById("as-sx");
        if (!cell) return;
        if (!sx) { cell.textContent = "—"; return; }
        cell.className = (Number(sx.chg_pct) || 0) >= 0 ? "u" : "d";
        var spc3 = sx.chg_pct ? sx.price / (1 + sx.chg_pct / 100) : null;
        cell.textContent = Number(sx.price).toLocaleString("en-IN") + (spc3 ? " (" + (sx.chg_pct >= 0 ? "+" : "−") + Math.abs(sx.price - spc3).toFixed(0) + ")" : "");
      });
    });
  }


  /* ---------- FORECAST RADAR (replaces AI head card) ---------- */
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
    /* v14 BUGFIX: purana check (indexOf !== 0) har innerHTML change pe true hota tha
       kyunki innerHTML "<div..." se shuru hota hai -> infinite fetch loop (site slow ho jaati thi).
       Ab sirf tab refetch jab FORECAST RADAR content hi na ho. */
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

  /* ---------- EVENT RADAR (ipo open/close pipeline events) ----------
     v14: chevron button (open/close expand), closed+upcoming IPO ka pura info,
     expand state auto-refresh ke baad bhi preserve */
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
      function esc2(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
      function ok(v) { return v != null && v !== "" && v !== "—"; }
      function row(e) {
        var x = byName[String(e.name || "").toLowerCase()] || {};
        var open = String(e.type || "").toUpperCase() === "OPEN";
        var d = e.date ? e.date.slice(8) + "/" + e.date.slice(5, 7) : "";
        var nm2 = String(e.name || "").replace(/ Limited$| Ltd$/i, "");
        var bits = [];
        if (ok(x.type)) bits.push(esc2(x.type));
        if (ok(x.status)) bits.push("Status: " + esc2(x.status));
        if (ok(x.price)) bits.push("Price " + esc2(x.price));
        if (ok(x.lot)) bits.push("Lot " + esc2(x.lot));
        if (ok(x.size)) bits.push("Size " + esc2(x.size));
        if (ok(x.open) || ok(x.close)) bits.push("Dates " + esc2(ok(x.open) ? x.open : "—") + " → " + esc2(ok(x.close) ? x.close : "—"));
        if (ok(x.listing)) bits.push("Listing " + esc2(x.listing));
        if (ok(x.sub)) bits.push("Sub " + esc2(x.sub));
        if (ok(x.gmp)) bits.push("GMP " + esc2(x.gmp));
        return '<details data-ev="' + esc2(nm2) + '"' + (evOpenState[nm2] ? ' open' : '') + ' style="margin-top:6px">' +
          '<summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap;list-style:none">' +
          '<b>' + esc2(nm2) + '</b>' +
          '<span style="margin-left:auto;font-weight:700;font-size:11.5px;color:' + (open ? "#77f37b" : "#ff8b8b") + '">' + esc2(e.type || "") + ' · ' + d + '</span>' +
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
    /* existing Events tile: only the word "Event", placed in TRADING group NEXT TO IPO tile */
    var tile = document.querySelector('a.tile[href="#events"]');
    var hg = document.querySelector("section#home .homegrid");
    if (tile) {
      var nm = tile.querySelector(".t-nm");
      if (nm) nm.textContent = "Event";
      tile.style.cssText = "";
      var ipo = document.querySelector('a.tile[href="ipo/"]');
      if (hg && ipo && ipo.parentNode === hg) hg.insertBefore(tile, ipo.nextSibling);
    }
    /* radar card on TOP inside the existing events section (before global calendar) */
    if (!document.getElementById("evCard")) {
      var sec = document.querySelector("section#events");
      if (sec) {
        var h2 = sec.querySelector("h2");
        if (h2) h2.textContent = "Event";
        var card = document.createElement("div");
        card.className = "card";
        card.id = "evCard";
        if (h2 && h2.nextSibling) sec.insertBefore(card, h2.nextSibling);
        else sec.appendChild(card);
      }
    }
    eventRadar();
  }

  /* ---------- status bar REMOVED (user request 25 Sep) — purana ho to hatao ---------- */
  function rmstatus() {
    try {
      var sb = document.querySelector(".as-status");
      if (sb && sb.parentNode) sb.parentNode.removeChild(sb);
    } catch (e) {}
  }

  function boot() { if (window.MB_LOCKED) return; rmstatus(); apply(); ticker(); desk(); watchAIHead(); buildEvents(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
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
  /* v14: light refresh 3 min (market hours) / full refresh 15 min - SAB sections automatic */
  function cycleLight() { try { ticker(); desk(); radarHead(); eventRadar(); } catch (e) {} }
  function cycleFull() {
    try {
      fmem = {};
      if (window.__MB_FLUSH) window.__MB_FLUSH();
      if (window.__MB_RERENDER) window.__MB_RERENDER();
    } catch (e) {}
    cycleLight();
  }
  setInterval(cycleFull, 900000);
  setInterval(function () { if (mktOpen()) cycleLight(); }, 180000);
})();
