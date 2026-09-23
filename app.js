/* MARKET BRAIN loader — pulls in the app in strict order (v=i: retry + skip on error, mf renamed mft).
   oldapp.js (main app) then patches (screener fix, TimesFM AI view, trade tools,
   learn + stage + guide + desktop, smart brain, MF tracker). */
(function () {
  "use strict";
  var __origSI = window.setInterval;
  window.__MB_INTERVALS = [];
  window.setInterval = function (fn, ms) {
    var id = __origSI(fn, ms);
    window.__MB_INTERVALS.push(id);
    return id;
  };
  var files = ["oldapp.js", "scrfix.js", "scrfix2.js", "aifix.js", "aifix2.js", "aifix3.js", "mbpatch.js", "dtfix.js", "brandfix.js", "tools.js", "tools1b.js", "tools2.js", "tools3.js", "tools4.js", "tools5.js", "learnfix.js", "stagefix.js", "guidefix.js", "deskfix.js", "bluefix2.js", "inputfix.js", "smart.js", "mft.js", "learnadd.js", "aibrain.js", "homefix.js", "learnfold.js", "macro.js", "gti.js", "manish.js", "gtiinfo.js", "oi.js", "powerpack.js", "money.js", "history.js", "bullish.js", "movement.js", "power2.js", "financelearn.js", "peers.js", "xray.js", "fdinvest.js", "newsvolume.js", "economypulse.js", "mbscore.js", "circuit.js", "bank.js", "stage.js", "bigplayer.js", "forda.js" ];
  var i = 0, tries = {};
  function banner(msg) {
    try {
      var d = document.createElement("div");
      d.textContent = msg;
      d.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999;background:#b91c1c;color:#fff;font:12px/1.6 sans-serif;padding:3px 8px;text-align:center";
      (document.body || document.documentElement).appendChild(d);
    } catch (e) {}
  }
  function next() {
    if (i >= files.length) return;
    var f = files[i++];
    var s = document.createElement("script");
    s.src = f + "?t=" + Date.now();
    s.async = false;
    s.onload = function () { tries[f] = 0; next(); };
    s.onerror = function () {
      tries[f] = (tries[f] || 0) + 1;
      if (tries[f] <= 2) { i--; setTimeout(next, 500); return; }
      banner("\u26A0 " + f + " load fail — page ek baar refresh karo");
      next();
    };
    document.head.appendChild(s);
  }
  next();
})();
