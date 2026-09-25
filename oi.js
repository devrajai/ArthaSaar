/* oi.js - GTI + Option Chain OI combo card (GTI section, zones ke neeche) */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function fmt(x) { return (Number(x) / 100000).toFixed(1) + "L"; }
  var DATA = null;
  function symBlock(name) {
    var s = DATA.symbols[name];
    if (!s) return "";
    var h = '<div class="note" style="margin-top:10px"><b style="font-size:15px">' + esc(name) + '</b> - Rs ' + esc(s.spot) + ' <span style="opacity:.7">(expiry ' + esc(s.expiry) + ')</span></div>';
    h += '<div class="note" style="display:flex;justify-content:space-between"><span style="color:#77f37b"><b>PUT wall</b> ' + esc(s.put_wall) + '</span><span style="opacity:.7">' + fmt(s.put_wall_oi) + ' OI</span></div>';
    h += '<div class="note" style="display:flex;justify-content:space-between"><span style="color:#ff8b8b"><b>CALL wall</b> ' + esc(s.call_wall) + '</span><span style="opacity:.7">' + fmt(s.call_wall_oi) + ' OI</span></div>';
    h += '<div class="note" style="display:flex;justify-content:space-between"><span>PCR <b>' + esc(s.pcr) + '</b> &middot; Max pain <b>' + esc(s.max_pain) + '</b></span><span style="opacity:.7">GTI POC ' + esc(s.gti.day_poc) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;font-size:11px;opacity:.6;margin-top:6px;padding:0 4px"><span>CALL OI (resistance)</span><span>STRIKE</span><span>PUT OI (support)</span></div>';
    for (var i = 0; i < s.chain.length; i++) {
      var c = s.chain[i];
      var atm = Math.abs(c.strike - s.spot) < (name.indexOf("BANK") === 0 ? 100 : 25);
      h += '<div class="note" style="display:flex;justify-content:space-between;font-size:12px;' + (atm ? 'border:1px solid rgba(255,213,77,.5);background:rgba(255,213,77,.08)' : '') + '"><span style="color:#ff8b8b">' + fmt(c.ce) + (c.ce_chg > 0 ? " \u25B2" : c.ce_chg < 0 ? " \u25BC" : "") + '</span><b>' + esc(c.strike) + '</b><span style="color:#77f37b">' + fmt(c.pe) + (c.pe_chg > 0 ? " \u25B2" : c.pe_chg < 0 ? " \u25BC" : "") + '</span></div>';
    }
    if (s.combo) {
      h += '<div class="note" style="margin-top:8px;background:rgba(30,144,255,.12);border:1px solid rgba(30,144,255,.35);border-radius:8px;padding:8px"><b style="color:#5fb0ff">GTI + OI COMBO</b><br>' + esc(s.combo.support) + '<br>' + esc(s.combo.resistance) + '<br><b>' + esc(s.combo.verdict) + '</b></div>';
    }
    return h;
  }
  function render() {
    var host = document.getElementById("oiCard");
    if (!host) return;
    var h = '<div class="subhead">GTI + Option Chain OI Combo</div>';
    h += '<div class="note">Option chain ki walls + GTI zones ek saath - jahan dono match kare = strongest level. (WAY2LAABH style)</div>';
    h += symBlock("NIFTY 50") + symBlock("BANKNIFTY");
    h += '<div class="footer-note">EOD bhavcopy se - roz raat update | PCR > 1 = put writers (bullish), < 0.85 = call writers (bearish) | ▲▼ = aaj ka OI change</div>';
    host.innerHTML = h;
  }
  function mount() {
    var sec = document.querySelector("#gtiMount") || document.querySelector("section#global");
    if (!sec || document.getElementById("oiCard")) return;
    var card = document.createElement("div");
    card.className = "card"; card.id = "oiCard"; card.style.marginTop = "14px";
    card.innerHTML = '<div class="subhead">GTI + OI Combo</div><div class="note"></div>';
    sec.appendChild(card);
    fetch("data/oi-gti.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) { DATA = d; render(); })
      .catch(function () {
        var b = document.getElementById("oiCard");
        if (b) b.innerHTML = '<div class="subhead">GTI + OI Combo</div><div class="note">data abhi nahi mila.</div>';
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
