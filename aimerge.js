/* aimerge.js v1 -- AI Forecast + AI Brain ko ek section me combine karta hai: AI BRAIN.
   DOM surgery (ArthaBodh jaisi): 2 home tiles -> 1 tile, #ai section ka content
   #aibrain me move (top pe forecast grid), #ai section remove. Data ek hi baar load. */
(function () {
  "use strict";
  var done = false;

  function merge() {
    if (done) return;
    var ai = document.getElementById("ai");
    var brain = document.getElementById("aibrain");
    if (!ai || !brain) { setTimeout(merge, 600); return; }
    done = true;

    /* 1. home grid: AI Forecast tile hatao, AI Brain tile subtitle update */
    try {
      var hg = document.querySelector("section#home .homegrid");
      var aiTile = hg ? hg.querySelector('a[href="#ai"]') : null;
      if (aiTile && aiTile.parentNode) aiTile.parentNode.removeChild(aiTile);
      var bTile = hg ? hg.querySelector('a[href="#aibrain"]') : null;
      if (bTile) {
        var sb = bTile.querySelector(".t-sb");
        if (sb) sb.textContent = "forecast \u00b7 mood \u00b7 crash \u00b7 report";
      }
    } catch (e) {}

    /* 2. h2 ke baad chhoti note line */
    try {
      var h2 = brain.querySelector("h2");
      if (h2 && h2.nextSibling) {
        var note = document.createElement("div");
        note.className = "note";
        note.style.cssText = "opacity:.7;margin:2px 0 8px";
        note.textContent = "do sections ek me: TimesFM 21-din forecast grid + mood meter, crash warning, report card, sector rotation";
        h2.parentNode.insertBefore(note, h2.nextSibling);
      }
    } catch (e) {}

    /* 3. #ai ka content #aibrain me move (backbtn/h2 skip), abMood se pehle */
    var abMood = brain.querySelector("#abMood");
    var label = document.createElement("div");
    label.className = "hgroup";
    label.textContent = "TIMESFM FORECAST \u2014 21-din AI predictions";
    if (abMood) brain.insertBefore(label, abMood);
    var kids = Array.prototype.slice.call(ai.children);
    for (var i = 0; i < kids.length; i++) {
      var k = kids[i];
      if (k.tagName === "A" && String(k.className).indexOf("backbtn") >= 0) continue;
      if (k.tagName === "H2") continue;
      if (abMood) brain.insertBefore(k, abMood); else brain.appendChild(k);
    }

    /* 3b. Dev (27 Sep): MARKET MOOD METER sabse upar -- forecast grid se pehle */
    if (abMood) {
      var hgl = brain.querySelector("div.hgroup");
      if (hgl) brain.insertBefore(abMood, hgl);
    }

    /* 4. #ai section hata do */
    if (ai.parentNode) ai.parentNode.removeChild(ai);

    /* 5. loader wrap: #aibrain par forecast bhi render ho */
    try {
      var L = (typeof loaders !== "undefined") ? loaders : window;
      var old = L.aibrain || null;
      L.aibrain = function () {
        if (typeof renderAI === "function") renderAI();
        if (typeof old === "function") old();
      };
    } catch (e) {}
  }

  function onHash() {
    var h = (location.hash || "").replace("#/", "#");
    var id = h.replace("#", "").split("/")[0];
    if (id !== "ai" && id !== "aibrain") return;
    merge();
    if (id === "ai") {
      try { history.replaceState(null, "", "#aibrain"); } catch (e) { location.hash = "#aibrain"; }
    }
    var secs = document.querySelectorAll("section[id]");
    for (var i = 0; i < secs.length; i++) {
      secs[i].style.display = secs[i].id === "aibrain" ? "" : "none";
    }
    try { if (typeof loaders !== "undefined" && loaders.aibrain) loaders.aibrain(); } catch (e) {}
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", onHash);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { merge(); onHash(); });
  } else { merge(); onHash(); }
})();
