/* cryptoradar.js v1 -- Crypto section ke top pe "Crypto Radar" card.
   Event radar + GTI zone style: FNG hero, market pulse, top movers bars.
   Data: data/crypto.json (Actions har 6 ghante laata hai - CoinGecko/Binance free). */
(function () {
  "use strict";

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function sign(v) { return v == null ? "\u2014" : (v >= 0 ? "+" : "") + v; }

  function fngInfo(v) {
    v = v == null ? 50 : v;
    if (v >= 75) return ["\ud83d\ude80 Extreme Greed", "#77f37b", "market bahut garam - Euphoria. Trend tikka hai par naye entry par dhyan"];
    if (v >= 55) return ["\ud83d\ude42 Greed", "#77f37b", "log khareed rahe hain - momentum positive"];
    if (v >= 45) return ["\ud83d\ude10 Neutral", "#eab308", "koi khaas jhalak nahi - wait and watch"];
    if (v >= 25) return ["\ud83d\ude13 Fear", "#f7b955", "log bech rahe hain - sasta mil sakta hai"];
    return ["\ud83d\ude31 Extreme Fear", "#ff8b8b", "market dar me hai - historically buying zone, par risk bhi zyada"];
  }

  function moverRow(c, gain) {
    var pct = c.chg_24h_pct == null ? 0 : c.chg_24h_pct;
    var w = Math.max(5, Math.min(100, Math.abs(pct) * 1.2));
    var col = gain ? "#77f37b" : "#ff8b8b";
    var nm = (c.name || c.symbol) + " (" + (c.symbol || "") + ")";
    var pr = c.price_usd == null ? "" : "$" + (c.price_usd >= 100 ? Math.round(c.price_usd).toLocaleString("en-IN") : c.price_usd.toFixed(c.price_usd >= 1 ? 2 : 4));
    var bar = gain ? "linear-gradient(90deg,#2f7a44,#77f37b)" : "linear-gradient(90deg,#a34a4a,#ff8b8b)";
    return '<div style="display:flex;align-items:center;gap:8px;margin:4px 0" title="' + esc(pr + " \u00b7 7d " + sign(c.chg_7d_pct) + "% \u00b7 30d " + sign(c.chg_30d_pct) + "% \u00b7 ATH se " + (c.from_ath_pct == null ? "?" : c.from_ath_pct + "%") + " neeche") + '">' +
      '<span style="width:118px;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(nm) + '</span>' +
      '<span style="flex:1;height:9px;border-radius:5px;background:rgba(255,255,255,.07);overflow:hidden"><i style="display:block;width:' + w + '%;height:100%;border-radius:5px;background:' + bar + '"></i></span>' +
      '<span style="width:54px;text-align:right;font-size:12px;font-weight:700;color:' + col + '">' + sign(pct) + "%</span></div>";
  }

  function render(d) {
    var box = document.getElementById("cryRadarBox");
    if (!box) return;
    var g = d.global || {}, fg = d.fear_greed || {};
    var fi = fngInfo(fg.value);
    var G = (d.gainers_24h || []).slice(0, 5);
    var L = (d.losers_24h || []).slice(0, 5);
    var h = '<div style="display:flex;align-items:center;gap:12px;margin:2px 0 6px">' +
      '<div style="font-size:38px;font-weight:700;line-height:1;color:' + fi[1] + '">' + (fg.value == null ? "\u2014" : fg.value) + '<span style="font-size:13px;opacity:.55">/100</span></div>' +
      '<div><div style="font-weight:700;color:' + fi[1] + ';font-size:14px">' + fi[0] + '</div>' +
      '<div class="note" style="font-size:11px;line-height:1.5">' + fi[2] + "</div></div></div>" +
      '<div style="height:10px;border-radius:5px;background:linear-gradient(90deg,#ff8b8b,#eab308,#77f37b);position:relative;margin:6px 0 4px">' +
      '<i style="position:absolute;top:-3px;left:' + Math.max(0, Math.min(97, (fg.value == null ? 50 : fg.value) - 1)) + '%;width:4px;height:16px;background:#fff;border-radius:2px;box-shadow:0 0 6px #fff"></i></div>' +
      '<div class="note" style="display:flex;justify-content:space-between;margin-bottom:8px"><span>Crypto Fear & Greed</span><span style="opacity:.6">0 dar \u00b7 100 lobh</span></div>';

    h += '<div class="note" style="display:flex;justify-content:space-between;margin:2px 0"><span>Total market cap</span><b>$' + (g.total_market_cap_usd ? (g.total_market_cap_usd / 1e12).toFixed(2) + "T" : "\u2014") +
      ' <span style="color:' + ((g.mcap_chg_24h_pct || 0) >= 0 ? "#77f37b" : "#ff8b8b") + ';font-size:11px">' + sign(g.mcap_chg_24h_pct) + "%</span></b></div>";
    h += '<div class="note" style="display:flex;justify-content:space-between;margin:2px 0"><span>BTC / ETH dominance</span><b>' + (g.btc_dominance != null ? g.btc_dominance + "%" : "\u2014") + ' <span style="opacity:.6;font-size:11px">/ ' + (g.eth_dominance != null ? g.eth_dominance + "%" : "\u2014") + "</span></b></div>";
    h += '<div class="note" style="display:flex;justify-content:space-between;margin:2px 0"><span>24h volume</span><b>$' + (g.total_volume_usd ? Math.round(g.total_volume_usd / 1e9) + "B" : "\u2014") + "</b></div>";

    if (G.length) {
      h += '<div class="subhead" style="margin-top:10px">\ud83d\ude80 Top gainers (24h)</div>' + G.map(function (c) { return moverRow(c, true); }).join("");
    }
    if (L.length) {
      h += '<div class="subhead" style="margin-top:8px">\ud83e\ude78 Top losers (24h)</div>' + L.map(function (c) { return moverRow(c, false); }).join("");
    }
    h += '<div class="note" style="margin-top:8px;opacity:.65">coin par tap = price \u00b7 7d \u00b7 30d \u00b7 ATH distance \u00b7 crypto 24x7 chalta hai \u2014 India market band ho tab bhi</div>';
    box.innerHTML = h;
  }

  function mount() {
    var sec = document.getElementById("crypto");
    if (!sec) return;
    if (document.getElementById("cryRadarCard")) { return; }
    var grid = sec.querySelector("#cryptoGlobal");
    var card = document.createElement("div");
    card.className = "card";
    card.id = "cryRadarCard";
    card.innerHTML =
      '<div class="subhead">\ud83d\udee1\ufe0f CRYPTO RADAR \u2014 market ka mood</div>' +
      '<div id="cryRadarBox"><div class="note">load ho raha...</div></div>' +
      '<div class="footer-note" style="margin-top:6px">har 6 ghante auto-update \u00b7 CoinGecko/Binance free data \u00b7 USD prices</div>';
    if (grid && grid.parentNode === sec) sec.insertBefore(card, grid);
    else sec.appendChild(card);
    try {
      jload("crypto").then(render, function () {
        var box = document.getElementById("cryRadarBox");
        if (box) box.innerHTML = '<div class="note">crypto data nahi mila \u2014 thodi der baad try karo</div>';
      });
    } catch (e) {}
  }

  var tries = 0;
  var t = setInterval(function () {
    tries++;
    if (document.getElementById("crypto")) { clearInterval(t); mount(); }
    if (tries > 120) clearInterval(t);
  }, 500);
})();
