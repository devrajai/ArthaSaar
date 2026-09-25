/* dtfix.js — times in AM/PM, dates as dd/mm/yy (IST).
   Loaded last: stops the old 24h clock, starts the AM/PM one,
   and auto-reformats any dates/times the app renders. */
(function () {
  (window.__MB_INTERVALS || []).forEach(function (id) { clearInterval(id); });
  var tf12 = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true });
  var dmyF = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kolkata",
    day: "2-digit", month: "2-digit", year: "2-digit" });
  var wdF = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "short" });
  var gp = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kolkata",
    weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false });
  function tick() {
    var now = new Date();
    $("#clock").textContent = tf12.format(now).toUpperCase();
    $("#clockdate").textContent = wdF.format(now) + ", " + dmyF.format(now) + " IST";
    var parts = gp.formatToParts(now);
    var gv = function (t) { return (parts.find(function (p) { return p.type === t; }) || {}).value || ""; };
    var day = gv("weekday"), hm = gv("hour") + gv("minute");
    var txt = "MARKET CLOSE", cls = "closed";
    if (["Sat", "Sun"].indexOf(day) === -1) {
      if (hm >= "0900" && hm < "0915") { txt = "PRE-OPEN"; cls = "pre"; }
      if (hm >= "0915" && hm <= "1530") { txt = "NSE OPEN"; cls = "open"; }
    }
    $("#mktTxt").textContent = txt; $("#mktDot").className = "dot " + cls;
  }
  tick(); setInterval(tick, 1000);

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function dmy(y, mo, d) { return d + "/" + mo + "/" + y.slice(2); }
  function ampm(h, m) {
    var h2 = +h % 12; if (h2 === 0) h2 = 12;
    return h2 + ":" + m + " " + (+h < 12 ? "AM" : "PM");
  }
  function fixStr(s) {
    return s
      .replace(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::\d{2})?(?:\s*UTC)?/g, function (_, y, mo, d, h, mi) {
        var t = new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi) + 19800000);
        return dmy(String(t.getUTCFullYear()), pad(t.getUTCMonth() + 1), pad(t.getUTCDate())) +
          ", " + ampm(t.getUTCHours(), pad(t.getUTCMinutes())) + " IST";
      })
      .replace(/(\d{2}):(\d{2})\s*UTC/g, function (_, h, mi) {
        var H = (+h + 5) % 24, M = +mi + 30;
        if (M >= 60) { M -= 60; H = (H + 1) % 24; }
        return ampm(H, pad(M)) + " IST";
      })
      .replace(/(\d{4})-(\d{2})-(\d{2})/g, function (_, y, mo, d) { return dmy(y, mo, d); });
  }
  function walk(node) {
    if (node.nodeType === 3) {
      var v = node.nodeValue;
      if (v && /(\d{4})-(\d{2})-(\d{2})|\d{2}:\d{2}\s*UTC/.test(v)) {
        var nv = fixStr(v);
        if (nv !== v) node.nodeValue = nv;
      }
      return;
    }
    if (node.nodeType !== 1 || node.tagName === "SCRIPT" || node.tagName === "STYLE") return;
    var it = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, null, false);
    var t;
    while ((t = it.nextNode())) {
      var v2 = t.nodeValue;
      if (v2 && /(\d{4})-(\d{2})-(\d{2})|\d{2}:\d{2}\s*UTC/.test(v2)) {
        var nv2 = fixStr(v2);
        if (nv2 !== v2) t.nodeValue = nv2;
    }
    }
  }
  var pend = null;
  new MutationObserver(function (muts) {
    for (var i = 0; i < muts.length; i++) {
      var t = muts[i].target;
      var el = t.nodeType === 1 ? t : t.parentElement;
      if (el && el.closest && el.closest(".clockbox, #mktPill")) return;
    }
    if (pend) clearTimeout(pend);
    pend = setTimeout(function () {
      pend = null;
      for (var j = 0;j < muts.length; j++) walk(muts[j].target);
    }, 200);
  }).observe(document.body, { childList: true, subtree: true, characterData: true });
})();
