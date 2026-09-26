/* ptsfix.js — VIX box + Crypto mini me % ke saath POINTS bhi (user request 26 Sep evening)
   oldapp ke render ke baad DOM patch karta hai — har 2 min re-apply. */
(function () {
  function pts(p, pc) {
    if (p == null || pc == null || isNaN(p) || isNaN(pc)) { return ""; }
    var v = p - p / (1 + pc / 100);
    var dp = Math.abs(v) >= 100 ? 0 : 2;
    if (v > 0) { return "+" + v.toFixed(dp) + " pts · "; }
    if (v < 0) { return "\u2212" + Math.abs(v).toFixed(dp) + " pts · "; }
    return "0 pts · ";
  }
  function patchVix() {
    fetch("data/indices-all.json?t=" + Date.now()).then(function (r) { return r.json(); })
      .then(function (d) {
        var box = document.getElementById("vixBox");
        if (!box) { return; }
        var b = box.querySelector("div.statline b");
        if (!b) { return; }
        var vix = null;
        var L = d.indices || [];
        for (var i = 0; i < L.length; i++) {
          if (L[i].index === "INDIA VIX") { vix = L[i]; break; }
        }
        if (!vix) { return; }
        b.textContent = nf2(vix.price) + " (" + pts(vix.price, vix.change_pct) +
          sign(vix.change_pct) + ")";
      }).catch(function () {});
  }
  function patchCrypto() {
    fetch("data/crypto.json?t=" + Date.now()).then(function (r) { return r.json(); })
      .then(function (d) {
        var box = document.getElementById("cryptoMini");
        if (!box) { return; }
        var bs = box.querySelectorAll("div.statline b");
        if (!bs.length) { return; }
        var top = d.top || [];
        var c = {};
        for (var i = 0; i < top.length; i++) { c[top[i].symbol] = top[i]; }
        var k = 0;
        var order = ["BTC", "ETH"];
        for (var j = 0; j < order.length; j++) {
          var it = c[order[j]];
          if (it && bs[k]) {
            bs[k].textContent = pts(it.price_usd, it.chg_24h_pct) + sign(it.chg_24h_pct);
            k++;
          }
        }
      }).catch(function () {});
  }
  function run() { patchVix(); patchCrypto(); }
  setTimeout(run, 3000);
  setInterval(run, 120000);
})();
