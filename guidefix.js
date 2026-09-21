/* guidefix.js — chart fix (modern TradingView embed), summary outline fix, site guide card */
(function () {
  /* 1. charts: replace legacy tv.js with official advanced-chart embed, rebuilt per symbol */
  var ivLabels = { "1": "1 min", "5": "5 min", "15": "15 min", "60": "1 hour", "D": "Daily" };
  function tvDraw(sym) {
    var full = (typeof tvSymbol === "function" ? tvSymbol(sym) : "NSE:" + sym);
    var box = $("#tvBox");
    if (!box) return;
    box.innerHTML = '<div class="tradingview-widget-container" style="height:430px;border-radius:12px;overflow:hidden">' +
      '<div class="tradingview-widget-container__widget" style="height:100%"></div></div>' +
      '<div class="footer-note" style="margin-top:6px">showing ' + esc(full) + " · " + (ivLabels[window.__mbIv || "D"] || window.__mbIv || "D") + "</div>";
    var s = document.createElement("script");
    s.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    s.async = true;
    s.type = "text/javascript";
    s.innerHTML = JSON.stringify({
      autosize: true, symbol: full, interval: window.__mbIv || "D",
      timezone: "Asia/Kolkata",
      theme: document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark",
      style: "1", locale: "en",
      hide_side_toolbar: true, allow_symbol_change: false,
      support_host: "https://www.tradingview.com"
    });
    box.insertBefore(s, box.firstChild);
  }
  window.renderCharts2 = function () {
    window.__mbIv = window.__mbIv || "D";
    window.__mbSym = window.__mbSym || "RELIANCE";
    var ivs = [["1", "1 min"], ["5", "5 min"], ["15", "15 min"], ["60", "1 hour"], ["D", "Daily"]];
    $("#chIv").innerHTML = ivs.map(function (v) {
      return '<button class="chip' + (window.__mbIv === v[0] ? " on" : "") + '" data-iv="' + v[0] + '">' + v[1] + "</button>";
    }).join("");
    $("#chIv").querySelectorAll(".chip").forEach(function (b) {
      b.onclick = function () {
        window.__mbIv = b.getAttribute("data-iv");
        window.__mbSym = $("#chSym").value.trim() || window.__mbSym;
        window.renderCharts2();
      };
    });
    tvDraw(window.__mbSym);
    $("#chGo").onclick = function () {
      var v = $("#chSym").value.trim();
      if (v) window.__mbSym = v;
      tvDraw(window.__mbSym);
    };
    $("#chSym").onkeydown = function (e) { if (e.key === "Enter") { var v = $("#chSym").value.trim(); if (v) window.__mbSym = v; tvDraw(window.__mbSym); } };
  };
  if (typeof loaders !== "undefined") loaders.charts = window.renderCharts2;

  /* 2. blue-line fix: no focus outline / tap highlight on details summaries */
  var st = document.createElement("style");
  st.textContent = "summary{outline:none;-webkit-tap-highlight-color:transparent}summary:focus{outline:none}details{border:0}";
  document.head.appendChild(st);
})();
