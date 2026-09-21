/* bluefix2.js — kill remaining blue sources (also in guidefix.js; belt and suspenders):
   selected chip bright blue border -> soft filled pill, details markers, tap highlight,
   tile :active stuck blue border */
(function () {
  var st = document.createElement("style");
  st.textContent =
    ".chip.on{background:var(--blue-dim);color:var(--blue);border-color:var(--border2)}" +
    "summary{list-style:none;outline:none;-webkit-user-select:none;user-select:none}" +
    "summary::-webkit-details-marker{display:none}" +
    "summary::marker{content:\"\"}" +
    "*{-webkit-tap-highlight-color:rgba(0,0,0,0)}" +
    ".tile:focus,.tile:focus-visible{outline:none}" +
    ".tile:active{border-color:rgba(255,255,255,.22)!important}";
  document.head.appendChild(st);
})();
