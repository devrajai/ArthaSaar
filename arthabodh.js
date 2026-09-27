/* arthabodh.js v1 -- Learn + Studies + My Notes teen sections ko ek me combine karta hai: ARTHABODH.
   DOM surgery: home ke 3 tiles ki jagah 1 tile, teen sections ka content ek naye
   section #arthabodh me move hota hai (listeners/cards safe rehte hain). */
(function () {
  "use strict";
  var UP = "#34d399";
  var done = false, rendered = false;

  function merge() {
    if (done) return;
    var learn = document.getElementById("learn");
    var studies = document.getElementById("studies");
    var mynotes = document.getElementById("mynotes");
    if (!learn || !studies || !mynotes) { setTimeout(merge, 600); return; }
    done = true;

    /* 1. home grid: 3 tiles -> 1 ArthaBodh tile */
    try {
      var hg = document.querySelector("section#home .homegrid");
      var anchor = hg ? hg.querySelector('a[href="#learn"]') : null;
      var tile = document.createElement("a");
      tile.className = "tile learnchip";
      tile.href = "#arthabodh";
      tile.innerHTML = '<span class="t-ic">\ud83d\udcda</span><span class="t-nm">ArthaBodh</span><span class="t-sb">school \u00b7 studies \u00b7 notes</span>';
      if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(tile, anchor);
        var st = hg ? hg.querySelector('a[href="#studies"]') : null;
        var mn = hg ? hg.querySelector('a[href="#mynotes"]') : null;
        if (st && st.parentNode) st.parentNode.removeChild(st);
        if (mn && mn.parentNode) mn.parentNode.removeChild(mn);
        if (anchor.parentNode) anchor.parentNode.removeChild(anchor);
      } else if (hg) {
        hg.appendChild(tile);
      }
    } catch (e) {}

    /* 2. naya section banao, teeno ka content daalo */
    var sec = document.createElement("section");
    sec.id = "arthabodh";
    sec.style.display = "none";
    var h = "";
    h += '<a class="backbtn" href="#home">\u2302 Home</a>';
    h += '<h2>ArthaBodh \u2014 padhai \u00b7 studies \u00b7 notes</h2>';
    h += '<div class="note" style="opacity:.7;margin:2px 0 8px">teen sections ek me: School (course, strategies, glossary, rules) + Studies (history heatmap) + My Notes (course notes)</div>';
    h += '<div class="subhead" style="margin-top:4px">School \u2014 Trading & Investing</div>';
    h += '<div id="abLearn"></div>';
    h += '<div class="subhead" style="margin-top:16px">Studies \u2014 history heatmap \u00b7 Sensex years \u00b7 Budget days</div>';
    h += '<div id="abStudies"></div>';
    h += '<div class="subhead" style="margin-top:16px">My Notes \u2014 Course Notes (Advance.pdf)</div>';
    h += '<div id="abNotes"></div>';
    sec.innerHTML = h;

    function moveInner(from, to) {
      var kids = Array.prototype.slice.call(from.children);
      for (var i = 0; i < kids.length; i++) {
        var k = kids[i];
        if (k.tagName === "A" && k.className.indexOf("backbtn") >= 0) continue; /* purana backbtn skip */
        if (k.tagName === "H2") continue; /* purana heading skip */
        to.appendChild(k);
      }
    }
    var w1 = sec.querySelector("#abLearn"), w2 = sec.querySelector("#abStudies"), w3 = sec.querySelector("#abNotes");
    moveInner(learn, w1);
    moveInner(studies, w2);
    moveInner(mynotes, w3);
    learn.parentNode.removeChild(learn);
    studies.parentNode.removeChild(studies);
    mynotes.parentNode.removeChild(mynotes);

    var foot = document.querySelector("footer");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(sec, foot);
    else document.body.appendChild(sec);
  }

  /* 3. render -- teeno loaders ek saath (oldapp.js ke global renderers) */
  function renderAll() {
    if (rendered) return;
    rendered = true;
    try { if (typeof renderLearn === "function") renderLearn(); } catch (e) {}
    try { if (typeof renderStudies === "function") renderStudies(); } catch (e) {}
    try { if (typeof renderNotes === "function") renderNotes(); } catch (e) {}
    try {
      if (window.__MB_RERENDER) window.__MB_RERENDER();
    } catch (e) {}
  }

  function isMine(id) {
    return id === "arthabodh" || id === "learn" || id === "studies" || id === "mynotes";
  }

  function onHash() {
    var h = (location.hash || "").replace("#/", "#");
    var id = h.replace("#", "").split("/")[0];
    if (!id || !isMine(id)) return;
    if (id !== "arthabodh") {
      try { history.replaceState(null, "", "#arthabodh"); } catch (e) { location.hash = "#arthabodh"; }
      id = "arthabodh";
    }
    merge();
    /* section khud dikhao (router ne pehle hi chhupa diya hoga) */
    var secs = document.querySelectorAll("section[id]");
    for (var i = 0; i < secs.length; i++) {
      secs[i].style.display = secs[i].id === "arthabodh" ? "" : "none";
    }
    renderAll();
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", onHash);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { merge(); onHash(); });
  } else {
    merge();
    onHash();
  }
})();