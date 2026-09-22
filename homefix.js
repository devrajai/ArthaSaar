/* homefix.js - Learn ke topics row: scroll down par chhupao, up par wapas */
(function () {
  var row = document.getElementById("learnChips");
  if (!row) return;
  var last = 0;
  window.addEventListener("scroll", function () {
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    if (y > last + 8 && y > 60) { row.style.display = "none"; }
    else if (last - y > 8) { row.style.display = ""; }
    last = y;
  }, { passive: true });
})();
