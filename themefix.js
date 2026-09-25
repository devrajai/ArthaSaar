/* themefix.js v9 - ARTHASAAR PREMIUM (reference header + radars, event tile on top, no small words):
   1) calm.css inject  2) infinity logo  3) favicon fix  4) ARtha-SAAR brand
   5) LIGHT/DARK pill button  6) gradient rline
   7) ticker tape  8) hero NIFTY panel (+SENSEX from global.json)
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

  /* ---------- SENSEX from global.json (yahoo ^BSESN) ---------- */
  function sensex(cb) {
    fetch("data/global.json").then(function (r) { return r.json(); }).then(function (d) {
      if (!d || !d.items) return cb(null);
      for (var k = 0; k < d.items.length; k++) {
        if (String(d.items[k].name || "").toUpperCase().indexOf("SENSEX") !== -1) return cb(d.items[k]);
      }
      cb(null);
    }).catch(function () { cb(null); });
  }

  /* ---------- ticker tape ---------- */
  function ticker() {
    fetch("data/indices-all.json").then(function (r) { return r.json(); }).then(function (d) {
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
        var v = (i.change_pct > 0 ? "+" : "") + (Number(i.change_pct) || 0).toFixed(2) + "%";
        parts.push("<span><b>" + w + "</b> " + Number(i.price).toLocaleString("en-IN") + " <span class='t " + c + "'>" + v + "</span></span>");
      });
      if (parts.length < 4) d.indices.slice(0, 8).forEach(function (i) {
        var c = (i.change_pct || 0) > 0 ? "u" : "d";
        parts.push("<span><b>" + i.index + "</b> " + Number(i.price).toLocaleString("en-IN") + " <span class='t " + c + "'>" + (i.change_pct > 0 ? "+" : "") + (Number(i.change_pct) || 0).toFixed(2) + "%</span></span>");
      });
      var one = parts.join("");
      var draw = function (sx) {
        if (sx) {
          var c2 = (sx.chg_pct || 0) > 0 ? "u" : "d";
          var sv = (sx.chg_pct > 0 ? "+" : "") + Number(sx.chg_pct).toFixed(2) + "%";
          var sSpan = "<span><b>SENSEX</b> " + Number(sx.price).toLocaleString("en-IN") + " <span class='t " + c2 + "'>" + sv + "</span></span>";
          one = sSpan + one;
        }
        tp.innerHTML = "<div class='as-tape-in'>" + one + one + "</div>";
      };
      sensex(draw);
    }).catch(function () {});
  }

  /* ---------- hero NIFTY panel (home top) ---------- */
  function desk() {
    fetch("data/indices-all.json").then(function (r) { return r.json(); }).then(function (d) {
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
        "<span class='" + (chg >= 0 ? "u" : "d") + "'>" + (chg >= 0 ? "▲" : "▼") + " " + Math.abs(chg).toFixed(2) + "%</span></div>" +
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
        cell.textContent = Number(sx.price).toLocaleString("en-IN");
      });
    }).catch(function () {});
  }


  /* ---------- FORECAST RADAR (replaces AI head card) ---------- */
  function radarHead() {
    fetch("data/timesfm_forecasts.json").then(function (r) { return r.json(); }).then(function (d) {
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
    }).catch(function () {});
  }

  function watchAIHead() {
    var el = document.getElementById("aiHead");
    if (!el) return;
    radarHead();
    var ob = new MutationObserver(function () {
      if (el.innerHTML.indexOf("FORECAST RADAR") !== 0) radarHead();
    });
    ob.observe(el, { childList: true, subtree: true });
  }

  /* ---------- EVENT RADAR (ipo open/close pipeline events) ---------- */
  function eventRadar() {
    fetch("ipo/data/terminal-events.json").then(function (r) { return r.json(); }).then(function (d) {
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
      var html = "";
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
    }).catch(function () {});
  }

  function buildEvents() {
    /* existing Events tile: only the word "Event", moved to TOP of homegrid */
    var tile = document.querySelector('a.tile[href="#events"]');
    var hg = document.querySelector("section#home .homegrid");
    if (tile) {
      var nm = tile.querySelector(".t-nm");
      if (nm) nm.textContent = "Event";
      if (hg) {
        tile.style.cssText = "grid-column:1/-1;flex-direction:row;align-items:center;gap:12px";
        hg.insertBefore(tile, hg.firstChild);
      }
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
})();
