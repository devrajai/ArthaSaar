/* stagefix.js — Stage Scanner card in Trade Tools (my 20/40 SMA stage rules, live data) */
(function () {
  var T = document.getElementById("tools");
  if (!T || document.getElementById("stageCard")) return;
  var where = document.getElementById("scanCard");
  var card = document.createElement("div");
  card.className = "card"; card.id = "stageCard";
  card.innerHTML = '<div class="subhead">Stage Scanner — my 20/40 rules on live data</div><div class="tblwrap" id="stageBody"><div class="loading">loading…</div></div>' +
    '<div class="footer-note">Stage 2 = price > 20EMA > 200EMA (breakout stage — buy zone) · Stage 4 = price < 20EMA < 200EMA (decline) · Stage 1 = base/consolidation near EMAs · Stage 3 = topping/reversal zone · EOD data</div>';
  if (where && where.nextSibling) T.insertBefore(card, where.nextSibling); else T.appendChild(card);

  function stageOf(s) {
    var p = s.price, e20 = s.ema20, e200 = s.ema200;
    if (!p || !e20 || !e200) return null;
    if (p > e20 && e20 > e200) return 2;
    if (p < e20 && e20 < e200) return 4;
    var d20 = Math.abs(p - e20) / p;
    if (d20 < 0.025 && Math.abs(p - e200) / p < 0.06) return 1;
    return 3;
  }
  function rowsFor(list, note) {
    if (!list.length) return '<tr><td colspan="4" class="loading">none today</td></tr>';
    return list.slice(0, 12).map(function (s) {
      return '<tr><td class="sym"><a href="#company/' + esc(s.symbol) + '">' + esc(s.symbol) + '</a></td>' +
        '<td>' + nf2(s.price) + '</td>' +
        '<td class="' + pctCls(s.change_pct) + '">' + sign(s.change_pct) + '</td>' +
        '<td>' + (s.rsi14 != null ? s.rsi14 : "—") + '</td></tr>';
    }).join("");
  }
  function renderStage() {
    jload("brain-screener").then(function (d) {
      var st = (d.stocks || []).map(function (s) { return {s: s, st: stageOf(s)}; }).filter(function (x) { return x.st; });
      var by = {1: [], 2: [], 3: [], 4: []};
      st.forEach(function (x) { by[x.st].push(x.s); });
      by[2].sort(function (a, b) { return (b.change_pct || 0) - (a.change_pct || 0); });
      by[4].sort(function (a, b) { return (a.change_pct || 0) - (b.change_pct || 0); });
      $("#stageBody").innerHTML =
        '<div class="statline" style="margin-bottom:8px"><span>Stage 1 (base)</span><b>' + by[1].length + '</b> <span>· Stage 2 (breakout)</span><b class="pos">' + by[2].length + '</b> <span>· Stage 3 (top)</span><b>' + by[3].length + '</b> <span>· Stage 4 (decline)</span><b class="neg">' + by[4].length + '</b></div>' +
        '<div class="subhead">Stage 2 — breakout candidates (buy zone, SKP-2 candle confirm)</div>' +
        '<table><thead><tr><th>Symbol</th><th>Price</th><th>Chg%</th><th>RSI14</th></tr></thead><tbody>' + rowsFor(by[2]) + '</tbody></table>' +
        '<div class="subhead">Stage 4 — decline (avoid / reversal wait)</div>' +
        '<table><thead><tr><th>Symbol</th><th>Price</th><th>Chg%</th><th>RSI14</th></tr></thead><tbody>' + rowsFor(by[4]) + '</tbody></table>';
    }, function () {
      $("#stageBody").innerHTML = '<div class="loading load-err">screener data unavailable</div>';
    });
  }
  var _rt = loaders.tools;
  if (_rt && !loaders._stWrap) {
    loaders._stWrap = true;
    loaders.tools = function () { try { _rt(); } catch (e) {} renderStage(); };
  }
})();
