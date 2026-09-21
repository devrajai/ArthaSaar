/* tools3.js — OI buildup table in Futures section */
(function () {
  var fs = document.querySelector("#futures");
  if (fs && !document.getElementById("oiCard")) fs.insertAdjacentHTML("beforeend",
    '<div class="card" id="oiCard"><div class="subhead">OI Buildup — near month (price × open interest)</div>' +
    '<div class="tblwrap"><table><thead><tr><th>Symbol</th><th>Price chg</th><th>OI chg</th><th>Buildup</th></tr></thead><tbody id="oiBody"></tbody></table></div>' +
    '<div class="footer-note">long buildup = price↑ OI↑ · short buildup = price↓ OI↑ · short covering = price↑ OI↓ · long unwinding = price↓ OI↓ · EOD bhavcopy</div></div>');

  function label(priceUp, oiUp) {
    if (priceUp && oiUp) return '<span class="pos">Long Buildup</span>';
    if (!priceUp && oiUp) return '<span class="neg">Short Buildup</span>';
    if (priceUp) return '<span class="pos">Short Covering</span>';
    return '<span class="neg">Long Unwinding</span>';
  }
  function idxChg(map, sym) {
    var core = sym.replace(/NIFTY/g, "");
    for (var k in map) {
      var n = k.replace(/[^A-Z]/g, "");
      if (n === sym || sym.indexOf(n) === 0 || (core && n.indexOf(core) >= 0 && n.indexOf("NIFTY") >= 0)) return map[k];
    }
    return null;
  }
  function renderOI() {
    Promise.allSettled([jload("futures"), jload("indices-all"), jload("brain-screener")]).then(function (R) {
      var F = R[0].status === "fulfilled" ? R[0].value : null;
      if (!F) { $("#oiBody").innerHTML = '<tr><td colspan="4" class="loading">unavailable</td></tr>'; return; }
      var imap = {}, smap = {};
      if (R[1].status === "fulfilled") (R[1].value.indices || []).forEach(function (i) { imap[i.symbol || i.index] = i.change_pct; });
      if (R[2].status === "fulfilled") (R[2].value.stocks || []).forEach(function (s) { smap[s.symbol] = s.change_pct; });
      var rows = [];
      (F.indices || []).forEach(function (ix) {
        var c = ix.contracts && ix.contracts[0]; if (!c) return;
        var chg = idxChg(imap, ix.symbol);
        if (chg == null) return;
        rows.push('<tr><td class="sym">' + esc(ix.symbol) + '</td>' +
          '<td class="' + pctCls(chg) + '">' + sign(chg) + '</td>' +
          '<td class="' + pctCls(c.oi_chg) + '">' + (c.oi_chg > 0 ? "+" : "") + Math.round(c.oi_chg / 1000) + 'k</td>' +
          '<td>' + label(chg > 0, c.oi_chg > 0) + '</td></tr>');
      });
      var st = (F.stocks || []).slice().sort(function (a, b) { return Math.abs(b.oi_chg || 0) - Math.abs(a.oi_chg || 0); }).slice(0, 15);
      st.forEach(function (s) {
        var chg = smap[s.symbol]; if (chg == null) return;
        rows.push('<tr><td class="sym"><a href="#company/' + esc(s.symbol) + '">' + esc(s.symbol) + '</a></td>' +
          '<td class="' + pctCls(chg) + '">' + sign(chg) + '</td>' +
          '<td class="' + pctCls(s.oi_chg) + '">' + (s.oi_chg > 0 ? "+" : "") + Math.round(s.oi_chg / 100000) + 'L</td>' +
          '<td>' + label(chg > 0, s.oi_chg > 0) + '</td></tr>');
      });
      $("#oiBody").innerHTML = rows.join("") || '<tr><td colspan="4" class="loading">no data today</td></tr>';
    });
  }
  var _rf = loaders.futures;
  if (_rf && !loaders._oiWrap) {
    loaders._oiWrap = true;
    loaders.futures = function () { try { _rf(); } catch (e) {} renderOI(); };
  }
})();
