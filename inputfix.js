/* inputfix.js — search boxes / gate password: focus border soft white, never blue */
(function () {
  var st = document.createElement("style");
  st.textContent =
    ".controls input:focus,.controls select:focus{border-color:var(--border2)!important}" +
    "#gInp:focus{border-color:rgba(255,255,255,.28)!important}" +
    "input:focus,select:focus,textarea:focus{outline:none}";
  document.head.appendChild(st);
})();
