/* calculators.js v1 -- daily-use calculators section (tile + section, self-mount).
   - Position size, Stop/Target R:R, Intraday charges, SIP, Lumpsum, EMI, Breakout
   - pure JS, koi external dep nahi. Inputs live update karte hain. */
(function () {
  "use strict";
  var UP = "#34d399", DN = "#ff8b8b";

  function esc(s) {
    if (s == null) s = "";
    return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; });
  }
  function inr(x) {
    if (!isFinite(x)) return "--";
    x = Math.round(x);
    var neg = x < 0; x = Math.abs(x);
    var s = x.toLocaleString("en-IN");
    return (neg ? "\u2212\u20b9" : "\u20b9") + s;
  }
  function n2(x) { return isFinite(x) ? x.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--"; }

  function inp(id, ph, val) {
    return '<input id="' + id + '" type="number" inputmode="decimal" placeholder="' + esc(ph) + '" value="' + (val == null ? "" : val) + '" ' +
      'style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:10px;border:1px solid rgba(125,180,255,.35);background:rgba(96,165,250,.08);color:inherit;font-size:14px;font-family:var(--mono)">';
  }
  function row(lab, html) {
    return '<div style="margin:8px 0"><div class="note" style="margin:2px 0">' + lab + '</div>' + html + '</div>';
  }
  function out(id) { return '<div id="' + id + '" class="note" style="margin-top:8px;font-family:var(--mono)"></div>'; }
  function g(id) { var e = document.getElementById(id); return e ? parseFloat(e.value) : NaN; }

  function bind(ids, fn) {
    function h() { try { fn(); } catch (e) {} }
    for (var i = 0; i < ids.length; i++) {
      var e = document.getElementById(ids[i]);
      if (e) { e.addEventListener("input", h); e.addEventListener("change", h); }
    }
  }

  /* ---------- 1. position size ---------- */
  function posSize() {
    var cap = g("cCap"), rp = g("cRisk"), en = g("cEnt"), sl = g("cSl");
    var o = document.getElementById("cPosOut"); if (!o) return;
    var riskAmt = cap * rp / 100;
    var per = Math.abs(en - sl);
    var qty = per > 0 ? Math.floor(riskAmt / per) : NaN;
    o.innerHTML = "Risk amount: <b style='color:" + DN + "'>" + inr(riskAmt) + "</b>" +
      "<br>Per-share risk: " + n2(per) +
      "<br>Quantity: <b style='color:" + UP + "'>" + (isFinite(qty) ? qty : "--") + " shares</b>" +
      (qty > 0 ? "<br>Position value: " + inr(qty * en) : "") +
      "<br><span style='opacity:.7'>1% risk = 100 trade tak account survive karega (rough rule)</span>";
  }

  /* ---------- 2. stop + target (R:R) ---------- */
  function rrCalc() {
    var en = g("cEnt2"), sl = g("cSl2"), tg = g("cTg");
    var o = document.getElementById("cRrOut"); if (!o) return;
    var risk = en - sl, rew = tg - en;
    if (!(Math.abs(risk) > 0)) { o.innerHTML = "entry aur stop alag rakho"; return; }
    var rr = rew / risk;
    o.innerHTML = "Risk/share: <span style='color:" + DN + "'>" + n2(Math.abs(risk)) + "</span>" +
      " &middot; Reward/share: <span style='color:" + UP + "'>" + n2(rew) + "</span>" +
      "<br><b>R:R = 1 : " + rr.toFixed(2) + "</b>" +
      (rr >= 2 ? " \u2014 achha trade" : rr >= 1 ? " \u2014 theek hai, 2+ better" : " \u2014 risk zyada hai, soch lo") +
      "<br><span style='opacity:.7'>40% win rate pe bhi 1:2 R:R = profitable</span>";
  }

  /* ---------- 3. intraday charges ---------- */
  function chgCalc() {
    var b = g("cBuy"), s = g("cSell"), q = g("cQty");
    var o = document.getElementById("cChgOut"); if (!o) return;
    if (!(q > 0) || !(b > 0) || !(s > 0)) { o.innerHTML = "teen values bharo"; return; }
    var buyT = b * q, sellT = s * q, tot = buyT + sellT;
    var brk = Math.min(20, buyT * 0.0003) + Math.min(20, sellT * 0.0003);
    var stt = sellT * 0.00025;
    var exch = tot * 0.0000297;
    var gst = (brk + exch) * 0.18;
    var sebi = tot * 0.000001;
    var stamp = buyT * 0.00003;
    var chg = brk + stt + exch + gst + sebi + stamp;
    var gross = (s - b) * q;
    var net = gross - chg;
    o.innerHTML = "Turnover: " + inr(tot) +
      "<br>Gross P&L: <b style='color:" + (gross >= 0 ? UP : DN) + "'>" + inr(gross) + "</b>" +
      "<br>Charges: <span style='color:#d4af37'>" + inr(chg) + "</span> (brokerage " + inr(brk) + " \u00b7 STT " + inr(stt) +
      " \u00b7 exch " + inr(exch + gst + sebi + stamp) + ")" +
      "<br>Net P&L: <b style='color:" + (net >= 0 ? UP : DN) + ";font-size:15px'>" + inr(net) + "</b>" +
      "<br><span style='opacity:.7'>approx (discount broker, intraday equity)</span>";
  }

  /* ---------- 4. SIP ---------- */
  function sipCalc() {
    var m = g("cSipM"), y = g("cSipY"), r = g("cSipR");
    var o = document.getElementById("cSipOut"); if (!o) return;
    var i = r / 1200, n = y * 12;
    var fv = i > 0 ? m * ((Math.pow(1 + i, n) - 1) / i) * (1 + i) : m * n;
    var inv = m * n;
    o.innerHTML = "Invested: " + inr(inv) +
      "<br>Estimated corpus: <b style='color:" + UP + "'>" + inr(fv) + "</b>" +
      "<br>Wealth gained: <b style='color:" + UP + "'>" + inr(fv - inv) + "</b>" +
      "<br><span style='opacity:.7'>monthly compounding @ " + r + "%</span>";
  }

  /* ---------- 5. lumpsum ---------- */
  function lsCalc() {
    var p = g("cLsP"), y = g("cLsY"), r = g("cLsR");
    var o = document.getElementById("cLsOut"); if (!o) return;
    var fv = p * Math.pow(1 + r / 100, y);
    o.innerHTML = "Invested: " + inr(p) +
      "<br>Value after " + y + " yrs: <b style='color:" + UP + "'>" + inr(fv) + "</b>" +
      "<br>Gained: <b style='color:" + UP + "'>" + inr(fv - p) + "</b> (" +
      (p > 0 ? ((fv / p - 1) * 100).toFixed(1) : "--") + "%)" +
      "<br><span style='opacity:.7'>annual compounding @ " + r + "%</span>";
  }

  /* ---------- 6. EMI ---------- */
  function emiCalc() {
    var p = g("cEmiP"), r = g("cEmiR"), m = g("cEmiM");
    var o = document.getElementById("cEmiOut"); if (!o) return;
    var i = r / 1200;
    var emi = i > 0 ? p * i * Math.pow(1 + i, m) / (Math.pow(1 + i, m) - 1) : p / m;
    o.innerHTML = "EMI: <b style='color:#d4af37'>" + inr(emi) + "/month</b>" +
      "<br>Total payment: " + inr(emi * m) +
      "<br>Interest: <span style='color:" + DN + "'>" + inr(emi * m - p) + "</span>" +
      "<br><span style='opacity:.7'>interest = " + (p > 0 ? ((emi * m - p) / p * 100).toFixed(0) : "--") + "% of loan</span>";
  }

  /* ---------- 7. breakout ---------- */
  function boCalc() {
    var hi = g("cBoH"), lo = g("cBoL"), buf = document.getElementById("cBoB").valueAsNumber || 0.1;
    var o = document.getElementById("cBoOut"); if (!o) return;
    var entry = hi * (1 + buf / 100), stop = lo, risk = entry - stop, tgt = entry + 2 * risk;
    o.innerHTML = "Buy above: <b style='color:" + UP + "'>" + n2(entry) + "</b>" +
      "<br>Stop-loss (day low): <span style='color:" + DN + "'>" + n2(stop) + "</span>" +
      "<br>Target (1:2): <b style='color:" + UP + "'>" + n2(tgt) + "</b>" +
      "<br><span style='opacity:.7'>buffer " + buf + "% \u00b7 agla din opening ke baad entry</span>";
  }

  function mount() {
    if (document.getElementById("calc")) return;
    /* tile -- TRADING group ke baad */
    try {
      var hg = document.querySelector("section#home .homegrid");
      var f = hg ? hg.querySelector('a[href="#futures"]') : null;
      var tile = document.createElement("a");
      tile.className = "tile";
      tile.href = "#calc";
      tile.innerHTML = '<span class="t-ic">\uD83E\uDDEE</span><span class="t-nm">Calculators</span><span class="t-sb">risk \u00b7 charges \u00b7 SIP</span>';
      if (f && f.nextSibling) hg.insertBefore(tile, f.nextSibling);
      else if (hg) hg.appendChild(tile);
    } catch (e) {}
    var sec = document.createElement("section");
    sec.id = "calc";
    sec.style.display = "none";
    sec.innerHTML =
      '<a class="backbtn" href="#home">\u2302 Home</a>' +
      '<h2>Calculators \u2014 daily use</h2>' +
      '<div class="grid g2">' +
      '<div class="card"><div class="subhead">Position Size</div>' +
      row("Capital (\u20b9)", inp("cCap", "50000", 50000)) +
      row("Risk per trade (%)", inp("cRisk", "1", 1)) +
      row("Entry", inp("cEnt", "100", 100)) +
      row("Stop-loss", inp("cSl", "98", 98)) +
      out("cPosOut") + '</div>' +
      '<div class="card"><div class="subhead">Target \u00b7 R:R</div>' +
      row("Entry", inp("cEnt2", "100", 100)) +
      row("Stop-loss", inp("cSl2", "98", 98)) +
      row("Target", inp("cTg", "104", 104)) +
      out("cRrOut") + '</div>' +
      '<div class="card"><div class="subhead">Intraday Charges</div>' +
      row("Buy price", inp("cBuy", "100", 100)) +
      row("Sell price", inp("cSell", "100.5", 100.5)) +
      row("Quantity", inp("cQty", "100", 100)) +
      out("cChgOut") + '</div>' +
      '<div class="card"><div class="subhead">SIP</div>' +
      row("Monthly (\u20b9)", inp("cSipM", "5000", 5000)) +
      row("Years", inp("cSipY", "10", 10)) +
      row("Expected return (%/yr)", inp("cSipR", "12", 12)) +
      out("cSipOut") + '</div>' +
      '<div class="card"><div class="subhead">Lumpsum</div>' +
      row("Amount (\u20b9)", inp("cLsP", "100000", 100000)) +
      row("Years", inp("cLsY", "10", 10)) +
      row("Return (%/yr)", inp("cLsR", "12", 12)) +
      out("cLsOut") + '</div>' +
      '<div class="card"><div class="subhead">EMI</div>' +
      row("Loan (\u20b9)", inp("cEmiP", "1000000", 1000000)) +
      row("Rate (%/yr)", inp("cEmiR", "9", 9)) +
      row("Months", inp("cEmiM", "60", 60)) +
      out("cEmiOut") + '</div>' +
      '</div>' +
      '<div class="card"><div class="subhead">Breakout \u2014 aane wale din ka setup</div>' +
      '<div class="grid g2">' +
      row("Aaj ka High", inp("cBoH", "100", 100)) +
      row("Aaj ka Low", inp("cBoL", "98", 98)) + '</div>' +
      row("Buffer (%)", inp("cBoB", "0.1", 0.1)) +
      out("cBoOut") + '</div>' +
      '<div class="footer-note">sab approximate hain \u2014 final numbers broker/exchange ke hisaab se thoda alag ho sakte hain</div>';
    var foot = document.querySelector("footer");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(sec, foot);
    else document.body.appendChild(sec);
    bind(["cCap", "cRisk", "cEnt", "cSl"], posSize);
    bind(["cEnt2", "cSl2", "cTg"], rrCalc);
    bind(["cBuy", "cSell", "cQty"], chgCalc);
    bind(["cSipM", "cSipY", "cSipR"], sipCalc);
    bind(["cLsP", "cLsY", "cLsR"], lsCalc);
    bind(["cEmiP", "cEmiR", "cEmiM"], emiCalc);
    bind(["cBoH", "cBoL", "cBoB"], boCalc);
    try { posSize(); rrCalc(); chgCalc(); sipCalc(); lsCalc(); emiCalc(); boCalc(); } catch (e) {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();