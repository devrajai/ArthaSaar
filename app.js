/* ARTHASAAR loader -- v13: PARALLEL download + ordered execution.
   Purana v12 sequential tha (ek file ka intezaar, phir agla request) —
   80 files x ~120ms latency = 10+ sec load. Ab saari files ek saath
   download hoti hain (HTTP/2 multiplex), execution order wahi rehta hai
   (async=false = ordered async scripts). Load ~1-2 sec. */
(function () {
  "use strict";
  var __origSI = window.setInterval;
  window.__MB_INTERVALS = [];
  window.setInterval = function (fn, ms) {
    var id = __origSI(fn, ms);
    window.__MB_INTERVALS.push(id);
    return id;
  };
  var files = ["oldapp.js", "gsearch.js", "kpifix.js", "scrfix.js", "scrfix2.js", "aifix.js", "aifix2.js", "aifix3.js", "mbpatch.js", "dtfix.js", "brandfix.js", "tools.js", "tools1b.js", "tools2.js", "tools3.js", "tools4.js", "tools5.js", "learnfix.js", "stagefix.js", "guidefix.js", "deskfix.js", "bluefix2.js", "inputfix.js", "smart.js", "mft.js", "learnadd.js", "aibrain.js", "homefix.js", "learnfold.js", "macro.js", "gti.js", "manish.js", "gtiinfo.js", "ict.js", "oi.js", "powerpack.js", "money.js", "history.js", "bullish.js", "movement.js", "power2.js", "financelearn.js", "peers.js", "xray.js", "fdinvest.js", "newsvolume.js", "news.js", "economypulse.js", "mbscore.js", "circuit.js", "bank.js", "stage.js", "bigplayer.js", "greeks.js", "globals.js", "alarm.js", "var.js", "playbook.js", "forda.js", "radars.js", "chartread.js","indicators.js", "alertscard.js", "results.js", "themefix.js", "ptsfix.js", "crtime.js", "dlvfix.js", "calculators.js", "journal.js", "rangefc.js","arthabodh.js",
   "eventradar.js",
   "cryptoradar.js",
   "aimerge.js" ];
  var tries = {};
  function load(f) {
    var s = document.createElement("script");
    s.src = f + "?v=as31";
    s.async = false; /* execution order preserve, download parallel */
    s.onload = function () { tries[f] = 0; };
    s.onerror = function () {
      try { if (s.parentNode) s.parentNode.removeChild(s); } catch (e) {}
      tries[f] = (tries[f] || 0) + 1;
      if (tries[f] <= 3) setTimeout(function () { load(f); }, 300 * tries[f]);
    };
    document.head.appendChild(s);
  }
  for (var j = 0; j < files.length; j++) load(files[j]);
})();
