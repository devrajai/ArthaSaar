/* MARKET BRAIN loader — pulls in the app in strict order:
   oldapp.js (main app) then patches (screener fix, TimesFM 3.0 AI view). */
(function () {
  "use strict";
  var files = ["oldapp.js", "scrfix.js", "scrfix2.js", "aifix.js", "aifix2.js", "aifix3.js", "mbpatch.js"];
  var i = 0;
  function next() {
    if (i >= files.length) return;
    var s = document.createElement("script");
    s.src = files[i++];
    s.async = false;
    s.onload = next;
    s.onerror = function () { console.error("MB load failed: " + s.src); };
    document.head.appendChild(s);
  }
  next();
})();
