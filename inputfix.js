/* inputfix.js — search boxes / gate password: focus border soft white, never blue;
   typing caret white; Learn-tile hardcoded blue border (learnchip) -> soft white */
(function () {
  var st = document.createElement("style");
  st.textContent =
    ".controls input:focus,.controls select:focus{border-color:var(--border2)!important}" +
    "#gInp:focus{border-color:rgba(255,255,255,.28)!important}" +
    "input:focus,select:focus,textarea:focus{outline:none}" +
    "input,select,textarea{caret-color:#e8eef7}" +
    "#gInp{caret-color:#e8eef7!important}" +
    ".learnchip{border-color:var(--border2)!important}";
  document.head.appendChild(st);
})();
