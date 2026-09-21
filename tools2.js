/* tools2.js — Trade Tools part 2: GTT planner + levels + Chartink scanners */
(function () {
  function drawGTT() {
    mbTool.drawNoteCard({key: "mb-gtt", card: "#gttCard", id: "g1", draw: drawGTT,
      head: "GTT-style price planner — if price hits level, do this",
      types: ["BUY", "SELL", "WATCH"],
      symPh: "SYMBOL e.g. RELIANCE", notePh: "note — e.g. breakout above 1400",
      empty: "no alerts yet — e.g. RELIANCE BUY at 1500",
      foot: '<div class="footer-note">planner only — place the actual GTT order in your broker app. Prices EOD.</div>'});
  }
  function drawTrend() {
    mbTool.drawNoteCard({key: "mb-trend", card: "#trendCard", id: "t1", draw: drawTrend,
      head: "My levels — support / resistance / trendlines",
      types: ["support", "resistance", "trendline", "buy zone", "target"],
      symPh: "SYMBOL e.g. RELIANCE", notePh: "note — e.g. 2022 low, strong support",
      empty: "no levels yet — e.g. RELIANCE support 1400",
      foot: '<div class="footer-note">saved on this phone (localStorage) — stays after refresh</div>'});
  }
  var SCANS = [
    ["RSI < 30 (oversold)", "https://chartink.com/screener/rsi-less30"],
    ["RSI cross 30/70", "https://chartink.com/screener/rsi-overbought-or-oversold-scan"],
    ["200 SMA crossover", "https://chartink.com/screener/200sma-crossover"],
    ["EMA 5 × EMA 20 cross", "https://chartink.com/screener/ema-5-crossing-above"],
    ["Lifetime highs", "https://chartink.com/screener/stocks-at-lifetime-high"],
    ["Weekly RSI OB/OS", "https://chartink.com/screener/weekly-rsi-overbought-oversold-scan"],
    ["Top loved scans", "https://chartink.com/screeners/top-loved-screeners"],
    ["Build your own", "https://chartink.com/screener"]
  ];
  function drawScan() {
    $("#scanCard").innerHTML = '<div class="subhead">Chartink quick scanners — one click, new tab</div>' +
      '<div class="chips">' + SCANS.map(function (s) {
        return '<a class="chip" href="' + s[1] + '" target="_blank" rel="noopener" style="text-decoration:none">' + s[0] + '</a>';
      }).join("") + '</div>' +
      '<div class="footer-note">full results need a free chartink.com login · embed blocked on free plan, so new tab</div>';
  }
  function renderTools() {
    drawScan();
    jload("brain-screener").then(function (d) {
      var bysym = {};
      (d.stocks || []).forEach(function (s) { bysym[s.symbol] = s; });
      window.__mbBySym = bysym; drawGTT(); drawTrend();
    }, function () { window.__mbBySym = {}; drawGTT(); drawTrend(); });
  }
  loaders.tools = renderTools;
  if ((location.hash || "").replace("#/", "#") === "#tools") window.showView("tools");
})();
