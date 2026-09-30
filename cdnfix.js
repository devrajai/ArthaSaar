/* cdnfix.js — (Oct 2026) repo private hai, isliye ab data /api/data proxy se aata hai.
   Purana note: cdnfix.js — data/ fetches jsDelivr CDN se (Vercel deployment 45MB -> ~2.5MB).
   Root page: "data/..." -> cdn.jsdelivr.net/gh/devrajai/ArthaSaar@main/data/...
   /ipo/ section apna data (ipo/data, 659K) deployment se hi leta hai — chhota hai.
   Freshness: candles.json + symbols.json candles.yml ke saath purge hote hain,
   baaki files cdn-purge.yml har 2 ghante purge karta hai. */
(function () {
  "use strict";
  var API = "/api/data?p=";
  var real = typeof window.fetch === "function" ? window.fetch.bind(window) : null;
  if (!real) return;
  var inIpo = false;
  try { inIpo = location.pathname.indexOf("/ipo") === 0; } catch (e) {}
  window.fetch = function (u, o) {
    try {
      if (!inIpo && typeof u === "string" && u.indexOf("://") < 0 && u.indexOf("data/") >= 0) {
        var m = u.match(/data\/[A-Za-z0-9._\-\/]+/);
        if (m) return real(API + encodeURIComponent(m[0]), o);
      }
    } catch (e) {}
    return real(u, o);
  };
})();
