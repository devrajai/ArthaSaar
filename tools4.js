/* tools4.js — common strategies (plain English + sample AFL logic) in Studies */
(function () {
  var ST = document.querySelector("#studies");
  if (!ST || document.getElementById("aflCard")) return;
  var S = [
    ["EMA crossover (5 × 20)", "trend following", "Buy jab 5-EMA 20-EMA ke upar cross kare. Exit jab wapas neeche cross ho. Sideways market mein whipsaw — sirf trending stocks par use karo. Sample AFL: Buy = Cross(EMA(C,5), EMA(C,20)); Sell = Cross(EMA(C,20), EMA(C,5));"],
    ["RSI mean reversion (14)", "oversold bounce", "Buy jab RSI(14) 30 ke neeche se upar aaye (oversold se nikalna). Exit RSI 60-70 par. Falling-knife risk — RSI akela kaafi nahi, level confirm karo. Sample AFL: Buy = Cross(RSI(14), 30); Sell = Cross(RSI(14), 60);"],
    ["Opening Range Breakout (ORB)", "intraday", "Pehle 15/30 min ka high-low note karo. High ke upar volume ke saath breakout = long; low ke neeche = short/exit. Stop = range ka doosra side. Volatile din mein range wide rakho."],
    ["Supertrend (10, 3)", "trailing stop system", "ATR-based line jo uptrend mein price ke neeche chalti hai. Line flip = entry/exit. Sideways mein false flips — 15min+ timeframe better. Sample AFL: Buy = C > Supertrend(10,3); Sell = C < Supertrend(10,3);"],
    ["Volume breakout", "confirmation filter", "Entry jab price 20-day high cross kare AUR volume 20-day average ka 2x ho. Bina volume ke breakout aksar fail. Sample AFL: Buy = C > Ref(HHV(C,20),-1) AND V > 2*MA(V,20);"],
    ["MACD signal cross", "momentum", "Buy jab MACD line signal line ke upar cross kare. Zero-line ke upar wala cross strong hota hai. Sample AFL: Buy = Cross(MACD(), Signal()); Sell = Cross(Signal(), MACD());"]
  ];
  ST.insertAdjacentHTML("beforeend", '<div class="card" id="aflCard">' +
    '<div class="subhead">Common strategies — plain English + sample AFL logic (educational, not signals)</div>' +
    S.map(function (x) {
      return '<details style="margin:8px 0"><summary><b>' + esc(x[0]) + '</b> <span class="footer-note">— ' + esc(x[1]) + '</span></summary><div class="note" style="margin-top:6px">' + esc(x[2]) + '</div></details>';
    }).join("") +
    '<div class="footer-note">AFL = Amibroker Formula Language · yahi logic TradingView Pine / chartink scan mein bhi banega · backtest first, small size first</div></div>');
})();
