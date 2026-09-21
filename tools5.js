/* tools5.js — Free Toolkit card: external free sites (links only, honest) */
(function () {
  var T = document.querySelector("#tools");
  if (!T || document.getElementById("mbToolkit")) return;
  var el = document.createElement("div");
  el.className = "card";
  el.id = "mbToolkit";
  var L = [
    ["Investar India — Lite (backtesting)", "https://www.investarindia.com/", "historical backtests, scans"],
    ["GoCharting — options charts", "https://gocharting.com/", "OP + OI chains, free tier"],
    ["Sensibull — options", "https://www.sensibull.com/", "option strategies, free tier"],
    ["StockEdge — MF + stock data", "https://web.stockedge.com/", "mutual funds, shareholding"],
    ["Screener.in — fundamentals", "https://www.screener.in/", "already used in Company Card"]
  ];
  el.innerHTML = '<div class="subhead">Free Toolkit — external sites (open in new tab)</div><ul style="margin:8px 0 4px 4px;list-style:none;font-size:13px;line-height:2">' +
    L.map(function (x) {
      return '<li><a href="' + x[1] + '" target="_blank" rel="noopener">' + esc(x[0]) + '</a> <span class="footer-note">— ' + esc(x[2]) + "</span></li>";
    }).join("") +
    "</ul>" +
    '<div class="footer-note">charts = TradingView (already embedded) · scanners = Chartink (already in Trade Tools above) · LuxAlgo = paid TradingView add-on, no free API — skip</div>';
  T.appendChild(el);
})();
