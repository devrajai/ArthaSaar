/* bluefix2.js — kills every non-design blue line:
   tile :active stuck blue border, input/select focus blue borders (search boxes,
   gate password), selected chip bright blue border, details markers, tap highlights */
(function () {
  var st = document.createElement("style");
  st.textContent =
    ".chip.on{background:var(--blue-dim);color:var(--blue);border-color:var(--border2)}" +
    "summary{list-style:none;outline:none;-webkit-user-select:none;user-select:none}" +
    "summary::-webkit-details-marker{display:none}" +
    "summary::marker{content:\"\"}" +
    "*{-webkit-tap-highlight-color:rgba(0,0,0,0)}" +
    ".tile:focus,.tile:focus-visible{outline:none}" +
    ".tile:active{border-color:rgba(255,255,255,.22)!important}" +
    ".controls input:focus,.controls select:focus{border-color:var(--border2)!important}" +
    "#gInp:focus{border-color:rgba(255,255,255,.28)!important}" +
    "input:focus,select:focus,textarea:focus{outline:none}";
  document.head.appendChild(st);
})();
