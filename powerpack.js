/* powerpack.js - Market Brain POWER PACK: Calculators + Greeks + Operator Radar + Dividends + Expiry Special
   Sab cards section#tools mein mount hote hain */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function inpt(id, ph, val) { return '<input id="' + id + '" placeholder="' + ph + '" value="' + (val || "") + '" style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:14px;margin-top:5px">'; }
  function getV(id) { var e = document.getElementById(id); return e ? parseFloat(e.value) || 0 : 0; }

  /* ---------- 1. CALCULATORS ---------- */
  function buildCalc(card) {
    card.innerHTML =
      '<div class="subhead">Trade Calculators (position sizing + R:R + brokerage)</div>' +
      '<div class="note" style="margin-top:8px"><b>Position Sizing</b> - Manish rule: max 10% risk</div>' +
      inpt("psCap", "Capital (Rs)", "35000") + inpt("psRisk", "Risk % per trade", "10") +
      inpt("psEntry", "Entry price", "23400") + inpt("psSL", "Stop loss price", "23365") +
      '<div class="note" id="psOut" style="margin-top:8px">values daalo...</div>' +
      '<div class="note" style="margin-top:10px"><b>Risk : Reward</b></div>' +
      inpt("rrEntry", "Entry", "23400") + inpt("rrSL", "SL", "23365") + inpt("rrTgt", "Target", "23480") +
      '<div class="note" id="rrOut" style="margin-top:8px">...</div>' +
      '<div class="note" style="margin-top:10px"><b>Brokerage (approx intraday)</b></div>' +
      inpt("brQty", "Quantity", "30") + inpt("brPrice", "Buy price", "23400") + inpt("brSell", "Sell price", "23440") +
      '<div class="note" id="brOut" style="margin-top:8px">...</div>' +
      '<div class="footer-note">qty = capital x risk% / (entry - SL) | brokerage ~0.05% roundtrip + STT</div>';
    function calcAll() {
      var cap = getV("psCap"), risk = getV("psRisk"), en = getV("psEntry"), sl = getV("psSL");
      var diff = en - sl, rAmt = cap * risk / 100;
      if (diff > 0) {
        var qty = Math.floor(rAmt / diff);
        document.getElementById("psOut").innerHTML =
          'Qty: <b>' + qty + '</b> | Risk: <b>Rs ' + Math.round(rAmt) + '</b> | T1 (1:1): <b>' + (en + diff).toFixed(1) +
          '</b> | T2 (1:2): <b>' + (en + 2 * diff).toFixed(1) + '</b><br>Manish check: Nifty ke liye min 25 pt capture, max 35 pt SL';
      } else { document.getElementById("psOut").textContent = "entry > SL hona chahiye"; }
      var re = getV("rrEntry"), rs = getV("rrSL"), rt = getV("rrTgt");
      var rr = (rt - re) / (re - rs);
      document.getElementById("rrOut").innerHTML = rr > 0 ?
        'R:R = <b>' + rr.toFixed(2) + ' : 1</b> ' + (rr >= 2 ? '(achha)' : '(kam - 1:2 chahiye)') : 'target entry ke galat side';
      var q = getV("brQty"), bp = getV("brPrice"), sp = getV("brSell");
      var gross = (sp - bp) * q, cost = (bp + sp) * q * 0.0006;
      document.getElementById("brOut").innerHTML = 'Gross P&L: <b>Rs ' + Math.round(gross) + '</b> | Charges ~Rs ' + Math.round(cost) + ' | Net: <b>Rs ' + Math.round(gross - cost) + '</b>';
    }
    ["psCap", "psRisk", "psEntry", "psSL", "rrEntry", "rrSL", "rrTgt", "brQty", "brPrice", "brSell"].forEach(function (id) {
      var e = document.getElementById(id);
      if (e) e.addEventListener("input", calcAll);
    });
    calcAll();
  }

  /* ---------- 2. GREEKS (Black-Scholes) ---------- */
  function nCdf(x) { return 0.5 * (1 + Math.tanh(0.7978845608 * (x + 0.044715 * x * x * x))); }
  function nPdf(x) { return Math.exp(-x * x / 2) / 2.50662827463; }
  function buildGreeks(card) {
    card.innerHTML =
      '<div class="subhead">Options Greeks Calculator (Black-Scholes)</div>' +
      '<div class="note" style="margin-top:8px">IV ke liye hint: India VIX se shuru karo</div>' +
      inpt("gS", "Spot price (S)", "23400") + inpt("gK", "Strike (K)", "23400") +
      inpt("gT", "Days to expiry", "7") + inpt("gIV", "Volatility % (IV)", "13") + inpt("gR", "Interest %", "6.5") +
      '<div class="note" id="gOut" style="margin-top:10px">values daalo...</div>' +
      '<div class="footer-note">Call delta 0.50 = ATM | 0.70+ ITM | deep OTM near 0</div>';
    function calc() {
      var S = getV("gS"), K = getV("gK"), T = getV("gT") / 365, v = getV("gIV") / 100, r = getV("gR") / 100;
      if (S <= 0 || K <= 0 || T <= 0 || v <= 0) return;
      var d1 = (Math.log(S / K) + (r + v * v / 2) * T) / (v * Math.sqrt(T)), d2 = d1 - v * Math.sqrt(T);
      var disc = Math.exp(-r * T), c = S * nCdf(d1) - K * disc * nCdf(d2), p = K * disc * nCdf(-d2) - S * nCdf(-d1);
      var deltaC = nCdf(d1), deltaP = deltaC - 1, gam = nPdf(d1) / (S * v * Math.sqrt(T));
      var the = -(S * nPdf(d1) * v) / (2 * Math.sqrt(T)) / 365;
      var veg = S * nPdf(d1) * Math.sqrt(T) / 100;
      document.getElementById("gOut").innerHTML =
        '<b>CALL:</b> Rs ' + c.toFixed(2) + ' (delta ' + deltaC.toFixed(3) + ')<br><b>PUT:</b> Rs ' + p.toFixed(2) +
        ' (delta ' + deltaP.toFixed(3) + ')<br>Gamma: ' + gam.toFixed(4) + ' (per lot delta change)<br>Theta: Rs ' + the.toFixed(2) +
        ' /day (time decay)<br>Vega: Rs ' + veg.toFixed(2) + ' (1% IV move)<br>' +
        (Math.abs(deltaC) > 0.6 ? 'ITM side' : Math.abs(deltaC) < 0.4 ? 'OTM side' : 'ATM - theta zyada khaata hai, Manish: ATM/OTM week-end mein mat kharido');
    }
    ["gS", "gK", "gT", "gIV", "gR"].forEach(function (id) {
      var e = document.getElementById(id);
      if (e) e.addEventListener("input", calc);
    });
    calc();
  }

  /* ---------- 3. OPERATOR RADAR ---------- */
  function buildRadar(card) {
    card.innerHTML = '<div class="subhead">Operator Radar (delivery % scanner - whale kahan hai)</div><div class="note">load ho raha hai...</div>';
    fetch("data/radar.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
      function row(s) { return '<div class="note" style="display:flex;justify-content:space-between"><span><b>' + esc(s.sym) + '</b> Rs ' + esc(s.close) + '</span><span style="color:' + (s.chg >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (s.chg >= 0 ? "+" : "") + s.chg + '% · ' + s.deliv + '% deliv</span></div>'; }
      var h = '<div class="note" style="margin-top:8px"><b style="color:#77f37b">ACCUMULATION</b> (high delivery + price upar - whale khareed raha):</div>';
      d.accumulation.slice(0, 10).forEach(function (s) { h += row(s); });
      h += '<div class="note" style="margin-top:10px"><b style="color:#ff8b8b">HIDDEN SELLING</b> (high delivery + price gir raha - bade haath bech raha):</div>';
      d.hidden_selling.slice(0, 6).forEach(function (s) { h += row(s); });
      h += '<div class="note" style="margin-top:10px"><b>VOLUME BLAST</b> (bade movers):</div>';
      d.volume_blast.slice(0, 6).forEach(function (s) { h += row(s); });
      h += '<div class="footer-note">data: ' + esc(d.date) + ' (NSE EOD delivery) - roz shaam update</div>';
      card.innerHTML = '<div class="subhead">Operator Radar (delivery % - whale kahan hai)</div>' + h;
    }).catch(function () { card.innerHTML = '<div class="subhead">Operator Radar</div><div class="note">data nahi mila.</div>'; });
  }

  /* ---------- 4. DIVIDEND CALENDAR ---------- */
  function buildDiv(card) {
    card.innerHTML = '<div class="subhead">Dividend / Bonus / Split Calendar</div><div class="note">load ho raha hai...</div>';
    fetch("data/dividends.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
      var h = "";
      if (!d.items || !d.items.length) {
        h = '<div class="note">aane wale hafte koi corporate action data file mein nahi (BSE announcements se collect hota hai - kal phir dekho)</div>';
      } else {
        d.items.slice(0, 20).forEach(function (x) {
          h += '<div class="note"><b>' + esc(x.sym) + '</b> <span style="opacity:.6">[' + esc(x.type) + ']</span> ' + esc(x.detail) + '</div>';
        });
      }
      h += '<div class="footer-note">' + esc(d.from) + ' se ' + esc(d.to) + ' tak | BSE announcements</div>';
      card.innerHTML = '<div class="subhead">Dividend / Bonus / Split Calendar</div>' + h;
    }).catch(function () { card.innerHTML = '<div class="subhead">Dividend Calendar</div><div class="note">data nahi mila.</div>'; });
  }

  /* ---------- 5. EXPIRY DAY SPECIAL ---------- */
  function buildExp(card) {
    card.innerHTML = '<div class="subhead">Expiry Day Special (NIFTY weekly)</div><div class="note">load ho raha hai...</div>';
    fetch("data/oi-gti.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
      var now = new Date();
      var tues = new Date(now); tues.setDate(now.getDate() + ((2 - now.getDay() + 7) % 7));
      var isExp = now.getDay() === 2;
      var days = Math.round((tues - now) / 86400000);
      var n = d.symbols["NIFTY 50"] || {};
      var h = '<div class="note" style="margin-top:8px;background:' + (isExp ? "rgba(255,165,0,.15)" : "rgba(30,144,255,.1)") + ';border:1px solid ' + (isExp ? "rgba(255,165,0,.4)" : "rgba(30,144,255,.3)") + ';border-radius:8px;padding:10px"><b style="color:' + (isExp ? "#ffb84d" : "#5fb0ff") + '">' +
        (isExp ? "AAJ EXPIRY HAI!" : "NIFTY expiry " + days + " din baad (" + ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][tues.getDay()] + ")") + '</b><br>Max pain: <b>' + esc(n.max_pain) + '</b> | PCR: <b>' + esc(n.pcr) + '</b><br>PUT wall ' + esc(n.put_wall) + ' (support) | CALL wall ' + esc(n.call_wall) + ' (resistance)</div>';
      h += '<div class="note" style="margin-top:10px"><b>Manish expiry rules:</b><br>1. 9:15-10:30 TRAP ZONE - option buying mat karo<br>2. Max pain ki taraf khinchav - expiry mostly max pain ke paas close hota hai<br>3. 2:30 ke baad hi asli move - tab trend ke saath<br>4. Deep OTM lottery nahi - whale ka khana ban jaoge (0.1% delta)<br>5. Walls (max OI strikes) strong support/resistance rehte hain expiry tak</div>';
      h += '<div class="footer-note">data: ' + esc(d.date) + ' EOD bhavcopy | GTI+OI card se</div>';
      card.innerHTML = '<div class="subhead">Expiry Day Special (NIFTY weekly)</div>' + h;
    }).catch(function () { card.innerHTML = '<div class="subhead">Expiry Special</div><div class="note">data nahi mila.</div>'; });
  }

  function mount() {
    var sec = document.querySelector("section#tools");
    if (!sec || document.getElementById("mbPower")) return;
    var defs = [["mbCalc", buildCalc], ["mbGreeks", buildGreeks], ["mbRadar", buildRadar], ["mbDiv", buildDiv], ["mbExp", buildExp]];
    defs.forEach(function (d0) {
      var c = document.createElement("div");
      c.className = "card"; c.id = d0[0]; c.style.marginTop = "14px";
      sec.appendChild(c);
      try { d0[1](c); } catch (e) { c.innerHTML = '<div class="subhead">Card error</div>'; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
