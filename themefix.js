/* themefix.js - CALM TERMINAL retheme (v3 approved UI):
   1) calm.css inject  2) naya logo (Bhoomi-Jyoti: earth + flame)  3) favicon MB leak fix
   4) ARtha-SAAR brand  5) ticker tape  6) bottom status bar  7) blue-green line
   Logo story: earth = grounded humble · flame = worst situation me roshni/energy/passion ·
   latitude arcs = learning experience ka daayra · dots = guidance (TG summary har jagah) */
(function () {
  "use strict";

  /* ---------- 1) calm.css ---------- */
  try {
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = "calm.css?t=" + Date.now();
    document.head.appendChild(l);
  } catch (e) {}

  /* ---------- logo SVGs ---------- */
  var GDEF = "<defs><linearGradient id='asg' x1='0' y1='0' x2='1' y2='1'>" +
    "<stop offset='0' stop-color='#7cc4ff'/><stop offset='1' stop-color='#7ce3a8'/></linearGradient></defs>";
  /* header logo: earth + flame, no text */
  var LOGO = "<svg viewBox='0 0 64 72' fill='none' xmlns='http://www.w3.org/2000/svg'>" + GDEF +
    "<circle cx='32' cy='46' r='16' stroke='url(#asg)' stroke-width='3'/>" +
    "<path d='M20 42c8 4 16 4 24 0' stroke='url(#asg)' stroke-width='1.4' opacity='.55'/>" +
    "<path d='M22 52c6 3.5 14 3.5 20 0' stroke='url(#asg)' stroke-width='1.4' opacity='.55'/>" +
    "<path d='M32 32c-6-4.5-7.5-10-4.5-15.5 1.2 3 2.4 4.2 4.5 5.4C31.5 12.8 33.6 8 38.5 4.5c-1.2 6.2-.3 9.3.8 12.4 1.6 5.2-1.7 11-7.3 15.1z' fill='url(#asg)'/>" +
    "<circle cx='46' cy='12' r='1.8' fill='#7ce3a8'/><circle cx='18' cy='16' r='1.3' fill='#7cc4ff'/>" +
    "</svg>";
  /* favicon: earth + flame + SAAR */
  var FAV = "<svg viewBox='0 0 64 76' fill='none' xmlns='http://www.w3.org/2000/svg'>" + GDEF +
    "<circle cx='32' cy='44' r='16' stroke='url(#asg)' stroke-width='3'/>" +
    "<path d='M20 40c8 4 16 4 24 0' stroke='url(#asg)' stroke-width='1.4' opacity='.55'/>" +
    "<path d='M22 50c6 3.5 14 3.5 20 0' stroke='url(#asg)' stroke-width='1.4' opacity='.55'/>" +
    "<path d='M32 30c-6-4.5-7.5-10-4.5-15.5 1.2 3 2.4 4.2 4.5 5.4C31.5 10.8 33.6 6 38.5 2.5c-1.2 6.2-.3 9.3.8 12.4 1.6 5.2-1.7 11-7.3 15.1z' fill='url(#asg)'/>" +
    "<circle cx='46' cy='10' r='1.8' fill='#7ce3a8'/>" +
    "<text x='32' y='72' font-family='Space Grotesk,Arial,sans-serif' font-size='11' font-weight='700' letter-spacing='2.5' text-anchor='middle' fill='#7cc4ff'>SAAR</text>" +
    "</svg>";

  /* ---------- 2) logo + 3) favicon + 4) brand ---------- */
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
    /* gradient line + ticker placeholder under header (sirf ek baar) */
    try {
      if (!document.querySelector(".as-rline")) {
        var hr = document.querySelector("header");
        if (hr && hr.parentNode) {
          var ln = document.createElement("div");
          ln.className = "as-rline";
          hr.parentNode.insertBefore(ln, hr.nextSibling);
          var tp = document.createElement("div");
          tp.className = "as-tape";
          tp.innerHTML = "<div class='as-tape-in'><b>ARTHASAAR</b>&nbsp;<span class='t'>market ka saar · shanti se dekho</span></div>";
          hr.parentNode.insertBefore(tp, ln.nextSibling);
        }
      }
    } catch (e) {}
  }

  /* ---------- 5) ticker tape (live data) ---------- */
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
      tp.innerHTML = "<div class='as-tape-in'>" + one + one + "</div>";
    }).catch(function () {});
  }

  /* ---------- 6) status bar ---------- */
  function statusbar() {
    try {
      if (document.querySelector(".as-status")) return;
      var s = document.createElement("div");
      s.className = "as-status";
      s.innerHTML = "<i class='s1'>EDUCATIONAL</i><i class='s2'>NOT ADVICE</i><i class='s3'>FREE SOURCES</i><i class='s4'>ARTHASAAR</i>";
      (document.body || document.documentElement).appendChild(s);
    } catch (e) {}
  }

  function boot() { apply(); statusbar(); ticker(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  /* gate ke baad body replace ho sakta hai — thoda baad me dobara apply */
  setTimeout(boot, 2500);
})();
