/* bluefix2.js — kill remaining blue-line sources:
   1. selected chip bright blue border -> soft filled pill (still clearly selected)
   2. plain <details> system marker (blue triangle on Android) -> hidden
   3. tap highlight + text selection on summaries -> off */
(function () {
  var st = document.createElement("style");
  st.textContent =
    ".chip.on{background:var(--blue-dim);color:var(--blue);border-color:var(--border2)}" +
    "summary{list-style:none;outline:none;-webkit-user-select:none;user-select:none}" +
    "summary::-webkit-details-marker{display:none}" +
    "summary::marker{content:\"\"}" +
    "*{-webkit-tap-highlight-color:rgba(0,0,0,0)}";
  document.head.appendChild(st);
})();
