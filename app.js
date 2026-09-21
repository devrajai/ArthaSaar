/* MARKET BRAIN loader — pulls in the app in strict order:
   oldapp.js (main app) then patches (screener fix, TimesFM 3.0 AI view,
   AM/PM clock + dd/mm/yy dates, trade tools, learn + stage + guide + desktop). */
(function () {
  "use strict";
  var __origSI = window.setInterval;
  window.__MB_INTERVALS = [];
  window.setInterval = function (fn, ms) {
    var id = __origSI(fn, ms);
    window.__MB_INTERVALS.push(id);
    return id;
  };
  var files = ["oldapp.js", "scrfix.js", "scrfix2.js", "aifix.js", "aifix2.js", "aifix3.js", "mbpatch.js", "dtfix.js", "brandfix.js", "tools.js", "tools1b.js", "tools2.js", "tools3.js", "tools4.js", "learnfix.js", "stagefix.js", "guidefix.js", "guide2.js", "deskfix.js"];
  var i = 0;
  function next() {
    if (i >= files.length) return;
    var s = document.createElement("script");
    s.src = files[i++] + "?t=" + Date.now();
    s.async = false;
    s.onload = next;
    s.onerror = function () { console.error("MB load failed: " + s.src); };
    document.head.appendChild(s);
  }
  next();
})();
