/* learnfold.js - Learn ke andar ke sab cards collapsible (Naye Tools jaise tap-to-open) */
(function () {
  var box = document.getElementById("eduBox");
  if (!box) return;
  function fold() {
    var cards = box.querySelectorAll(".card");
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      var sh = c.querySelector(".subhead");
      if (!sh) continue;
      var d = document.createElement("details");
      d.className = "gl";
      var s = document.createElement("summary");
      s.innerHTML = "<b>" + sh.textContent + "</b>";
      d.appendChild(s);
      c.removeChild(sh);
      while (c.firstChild) d.appendChild(c.firstChild);
      if (c.parentNode) c.parentNode.replaceChild(d, c);
    }
  }
  fold();
  if (window.MutationObserver) new MutationObserver(fold).observe(box, { childList: true, subtree: true });
})();
