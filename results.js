/* results.js — Q2 results calendar card (Events section me, Event Radar ke baad).
   Data: data/results.json — exchange filings se confirmed dates. */
(function () {
  "use strict";
  var R = null;
  var MOUNTED = false;
  function esc(s) {
    if (s == null) { s = ""; }
    return String(s).replace(/[&<>"']/g, function (c) {
      return "&#" + c.charCodeAt(0) + ";";
    });
  }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var DAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  function fmt(d) {
    var p = d.split("-");
    var dt = new Date(+p[0], +p[1] - 1, +p[2]);
    return DAY[dt.getDay()] + " " + dt.getDate() + " " + MON[dt.getMonth()];
  }
  function panel() {
    if (!R || !R.results) return '<div class="note">results data nahi mila.</div>';
    var res = R.results.slice().sort(function (a, b) {
      var ka = a.date || "9999"; var kb = b.date || "9999";
      return ka < kb ? -1 : (ka > kb ? 1 : 0);
    });
    var today = new Date().toISOString().slice(0, 10);
    var byDate = {};
    for (var i = 0; i < res.length; i++) {
      var r = res[i];
      if (r.date && r.date < today) continue;
      var k = r.date || "expected";
      if (!byDate[k]) byDate[k] = [];
      byDate[k].push(r);
    }
    var keys = Object.keys(byDate);
    if (!keys.length) return '<div class="note">is season ke saare dates nikal gaye — naya season aane par update karunga.</div>';
    var h = "";
    for (var j = 0; j < keys.length; j++) {
      var kk = keys[j];
      if (kk === "expected") {
        for (var m = 0; m < byDate[kk].length; m++) {
          var e = byDate[kk][m];
          h += '<div style="display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px solid #333">' +
            '<span>' + esc(e.company) + ' <span class="note">(' + esc(e.sym || "") + ')</span></span>' +
            '<span class="note">' + esc(e.expected || "date aane wali hai") + "</span></div>";
        }
        continue;
      }
      var parts = [];
      for (var q = 0; q < byDate[kk].length; q++) {
        var it = byDate[kk][q];
        var t = esc(it.company);
        if (it.div) t += ' <span class="note">· ' + esc(it.div) + "</span>";
        if (it.call) t += ' <span class="note">· call ' + esc(it.call) + "</span>";
        if (it.conf === false) t += ' <span class="note">(tentative)</span>';
        parts.push(t);
      }
      h += '<div style="padding:5px 0;border-bottom:1px solid #333">' +
        '<b style="font-family:var(--mono,monospace)">' + fmt(kk) + "</b>" +
        '<div style="margin-top:2px">' + parts.join(" · ") + "</div></div>";
    }
    return h + '<div class="note" style="margin-top:6px">exchange filings se · naye dates aate hi update hongi</div>';
  }
  function draw() {
    var host = document.getElementById("resCard");
    if (!host) return false;
    host.innerHTML = panel();
    return true;
  }
  function mount() {
    if (MOUNTED || document.getElementById("resCard")) { return; }
    var ev = document.getElementById("events");
    if (!ev) return;
    var card = document.createElement("div");
    card.className = "card";
    card.innerHTML = '<div class="subhead">Results Calendar — ' + (R && R.quarter ? esc(R.quarter) : "Q2 FY27") + '</div><div id="resCard"></div>';
    ev.appendChild(card);
    MOUNTED = true;
    draw();
  }
  function boot() {
    fetch("data/results.json?t=" + Date.now())
      .then(function (r) { return r.json(); })
      .then(function (d) { R = d; mount(); draw(); })
      .catch(function () {});
  }
  var iv = setInterval(function () {
    if (MOUNTED) { clearInterval(iv); return; }
    mount();
  }, 3000);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
