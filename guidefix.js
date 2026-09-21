/* guidefix.js — chart: direct TradingView iframe (symbol in URL, cannot default) + US tickers + blue-border kill */
(function () {
  var US = { AAPL:"NASDAQ", MSFT:"NASDAQ", GOOGL:"NASDAQ", AMZN:"NASDAQ", NVDA:"NASDAQ", TSLA:"NASDAQ", META:"NASDAQ", AMD:"NASDAQ", INTC:"NASDAQ", NFLX:"NASDAQ", PYPL:"NASDAQ", COIN:"NASDAQ", MSTR:"NASDAQ", PLTR:"NASDAQ", QQQ:"NASDAQ", BABA:"NYSE", BAC:"NYSE", JPM:"NYSE", WMT:"NYSE", KO:"NYSE", DIS:"NYSE", V:"NYSE", MA:"NYSE", UBER:"NYSE", SPY:"AMEX" };
  function tvFull(sym) {
    var x = (sym || "").trim().toUpperCase();
    if (x && US[x]) return US[x] + ":" + x;
    if (typeof tvSymbol === "function") return tvSymbol(sym);
    return x ? "NSE:" + x : "NSE:RELIANCE";
  }
  function tvDraw(sym) {
    var full = tvFull(sym), box = $("#tvBox");
    if (!box) return;
    var iv = window.__mbIv || "D";
    var labels = { "1": "1 min", "5": "5 min", "15": "15 min", "60": "1 hour", "D": "Daily" };
    var theme = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    var src = "https://s.tradingview.com/widgetembed/?symbol=" + encodeURIComponent(full) +
      "&interval=" + encodeURIComponent(iv) + "&theme=" + theme + "&style=1&locale=en" +
      "&timezone=" + encodeURIComponent("Asia/Kolkata") +
      "&hide_side_toolbar=true&allow_symbol_change=false&withdateranges=true&save_image=false&hideideas=1";
    box.innerHTML = '<iframe src="' + src + '" allowtransparency="true" frameborder="0" scrolling="no" style="width:100%;height:460px;border:0;border-radius:12px;overflow:hidden;background:rgba(255,255,255,.03)"></iframe>' +
      '<div class="footer-note" style="margin-top:6px">showing ' + esc(full) + " · " + (labels[iv] || iv) + " · chart by TradingView · US: AAPL, TSLA, NVDA… type any</div>";
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
        var v = $("#chSym").value.trim(); if (v) window.__mbSym = v;
        tvDraw(window.__mbSym);
      };
    });
    tvDraw(window.__mbSym);
    $("#chGo").onclick = function () {
      var v = $("#chSym").value.trim();
      if (v) window.__mbSym = v;
      tvDraw(window.__mbSym);
    };
    $("#chSym").onkeydown = function (e) {
      if (e.key === "Enter") {
        var v = $("#chSym").value.trim();
        if (v) window.__mbSym = v;
        tvDraw(window.__mbSym);
      }
    };
  };
  if (typeof loaders !== "undefined") loaders.charts = window.renderCharts2;
  /* blue-border kill: focus outlines, tap highlights, AND tile :active blue (stuck border) */
  var st = document.createElement("style");
  st.textContent = "summary{outline:none;-webkit-tap-highlight-color:transparent}summary:focus{outline:none}button:focus{outline:none}a:focus{outline:none}a:focus-visible{outline:none}details{border:0}.chip{-webkit-tap-highlight-color:transparent}.tile{outline:none;-webkit-tap-highlight-color:transparent}.tile:focus{outline:none}.tile:focus-visible{outline:none}.tile:active{border-color:rgba(255,255,255,.22)!important}";
  document.head.appendChild(st);
})();
