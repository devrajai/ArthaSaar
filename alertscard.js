/* alertscard.js — Chart Reading section me "Tere Alerts" card (data/alerts.json).
   Price alerts TG pe jaate hain (smart_alert.py har 15 min market hours me check karta hai). */
(function () {
  "use strict";
  var A = null, C = null;
  var UP = "#22c55e", DN = "#ef4444";
  function esc(s) {
    if (s == null) { s = ""; }
    return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; });
  }
  function n2(x) { return Number(x).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function lastClose(sym) {
    if (!C || !C.syms || !C.syms[sym]) return null;
    var d = C.syms[sym];
    var t = d["5m"] || d["15m"] || d["1h"];
    if (!t || !t.c || !t.c.length) return null;
    return t.c[t.c.length - 1];
  }
  function panel() {
    if (!A) return '<div class="note">alerts data nahi mila.</div>';
    var list = A.alerts || [];
    if (!list.length) return '<div class="note">koi alert set nahi - Dev ko bolo jaise: NIFTY 23500 upar cross ho to batao. TG pe message aayega.</div>';
    var h = "";
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      var dist = "";
      var l = lastClose(a.symbol);
      if (l != null) {
        var off = a.level - l;
        dist = " | abhi " + n2(l) + " se " + (off > 0 ? "+" : "-") + Math.abs(off).toFixed(0);
      }
      var below = a.dir === "below";
      h += '<div class="lrow" style="display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px solid #333">' +
        '<span>' + esc(a.symbol) + (below ? " neeche" : " upar") + "</span>" +
        '<span style="font-family:var(--mono,monospace);color:' + (below ? DN : UP) + '">' +
        n2(a.level) + (a.note ? " <span class='note' style='color:#888'>- " + esc(a.note) + "</span>" : "") +
        "<span class='note' style='color:#888'>" + dist + "</span></span></div>";
    }
    return h + '<div class="note" style="margin-top:6px">market hours me har 15 min check hota hai | fire hone par alert hata jata hai</div>';
  }
  function mount() {
    if (document.getElementById("crAlerts")) return true;
    var host = document.getElementById("chartread");
    if (!host) return false;
    var card = document.createElement("div");
    card.className = "card";
    card.innerHTML = '<div class="subhead">Tere Alerts — level cross hone par TG pe</div><div id="crAlerts"></div>';
    var vp = document.getElementById("crVP");
    if (vp && vp.parentNode) vp.parentNode.insertBefore(card, vp.nextSibling);
    else host.appendChild(card);
    return true;
  }
  function draw() {
    var el = document.getElementById("crAlerts");
    if (el) el.innerHTML = panel();
  }
  var iv = setInterval(function () {
    if (mount()) { draw(); clearInterval(iv); }
  }, 3000);
  fetch("data/alerts.json?t=" + Date.now())
    .then(function (r) { return r.json(); })
    .then(function (d) { A = d; if (mount()) draw(); })
    .catch(function () {});
  fetch("data/candles.json?t=" + Date.now())
    .then(function (r) { return r.json(); })
    .then(function (d) { C = d; if (mount()) draw(); })
    .catch(function () {});
})();
