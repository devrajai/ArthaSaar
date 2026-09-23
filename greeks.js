/* greeks.js - OPTION GREEKS + LTP CALCULATOR: har F&O stock/index ka EOD greeks chain + Black-Scholes calculator. #screener */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var D = null, CUR = "NIFTY", EI = 0;

  // Black-Scholes (JS) - LTP calculator ke liye
  function nrm(x) { var t = 1 / (1 + 0.2316419 * Math.abs(x)); var d = 0.3989423 * Math.exp(-x * x / 2); var p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return x > 0 ? 1 - p : p; }
  function phi(x) { return Math.exp(-x * x / 2) / Math.sqrt(2 * Math.PI); }
  function bsAll(S, K, days, r, iv, typ) {
    var T = Math.max(days, 0.25) / 365, sig = iv / 100;
    if (S <= 0 || K <= 0 || sig <= 0) return null;
    var d1 = (Math.log(S / K) + (r + sig * sig / 2) * T) / (sig * Math.sqrt(T)), d2 = d1 - sig * Math.sqrt(T);
    var px, delta, theta;
    if (typ === "c") { px = S * nrm(d1) - K * Math.exp(-r * T) * nrm(d2); delta = nrm(d1); theta = (-S * phi(d1) * sig / (2 * Math.sqrt(T)) - r * K * Math.exp(-r * T) * nrm(d2)) / 365; }
    else { px = K * Math.exp(-r * T) * nrm(-d2) - S * nrm(-d1); delta = nrm(d1) - 1; theta = (-S * phi(d1) * sig / (2 * Math.sqrt(T)) + r * K * Math.exp(-r * T) * nrm(-d2)) / 365; }
    return { px: px, delta: delta, gamma: phi(d1) / (S * sig * Math.sqrt(T)), theta: theta, vega: S * phi(d1) * Math.sqrt(T) / 100 };
  }

  function calcBox() {
    var q = function (id) { return parseFloat(document.getElementById(id).value) || 0; };
    var S = q("grS"), K = q("grK"), days = q("grD"), iv = q("grIV");
    var r = q("grR") || 6.5, typ = document.getElementById("grT").value;
    var a = bsAll(S, K, days, r / 100, iv, typ);
    var out = document.getElementById("grOut");
    if (!a) { out.innerHTML = "<span class='note'>inputs bharo (IV 10-80% typical)</span>"; return; }
    out.innerHTML = "<b style='font-size:15px'>\u20B9" + a.px.toFixed(2) + "</b>" +
      " <span style='font-size:11px;opacity:.6'>(LTP/fair value)</span>" +
      " \u00b7 \u0394 " + a.delta.toFixed(2) + " \u00b7 \u0393 " + a.gamma.toFixed(4) +
      " \u00b7 \u0398 " + a.theta.toFixed(2) + "/din \u00b7 \u03BD " + a.vega.toFixed(2) +
      " <span style='font-size:10.5px;opacity:.5'>(theta = roz ki jalne ki speed, vega = 1% IV move ka asar)</span>";
  }

  function chain(u, ei) {
    var c = u.c[ei];
    var h = '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px"><b>' + esc(CUR) + '</b> <span style="font-size:12px;opacity:.7">\u20B9' + esc(u.s) + '</span>' +
      '<span style="margin-left:auto;font-size:10.5px;opacity:.6">' + esc(D.updated) + ' EOD</span></div>';
    h += '<div style="display:flex;gap:5px;margin-top:6px">' + u.c.map(function (x, i) {
      return '<span data-ei="' + i + '" class="grExp" style="font-size:11px;padding:4px 9px;border-radius:8px;cursor:pointer;border:1px solid ' + (i === ei ? "rgba(240,180,41,.7)" : "rgba(255,255,255,.15)") + ';background:' + (i === ei ? "rgba(240,180,41,.15)" : "transparent") + '">' + esc(x.d.slice(5)) + '</span>';
    }).join("") + '</div>';
    h += '<div style="display:flex;font-size:10px;opacity:.55;margin-top:8px;padding:0 2px"><span style="flex:1">STRIKE</span><span style="flex:2.2">CE \u20B9 \u00b7 \u0394 \u00b7 \u0398 \u00b7 IV</span><span style="flex:2.2;text-align:right">PE \u20B9 \u00b7 \u0394 \u00b7 \u0398 \u00b7 IV</span></div>';
    c.r.forEach(function (row) {
      var K = row[0];
      var atm = Math.abs(K - u.s) === Math.min.apply(null, c.r.map(function (r) { return Math.abs(r[0] - u.s); }));
      h += '<div style="display:flex;font-size:11.5px;padding:5px 2px;margin-top:2px;border-radius:7px;' + (atm ? "background:rgba(240,180,41,.1);border:1px solid rgba(240,180,41,.25)" : "border:1px solid rgba(255,255,255,.06)") + '">' +
        '<b style="flex:1' + (atm ? ';color:rgba(240,180,41,.95)"' : '"') + '>' + esc(K) + (atm ? " \u2B50" : "") + '</b>' +
        '<span style="flex:2.2;color:' + (row[2] > 0 ? "#77f37b" : "#ff8b8b") + '">' + (row[1] != null ? "\u20B9" + esc(row[1]) + " \u00b7 \u0394" + esc(row[3]) + " \u00b7 \u0398" + esc(row[4]) + " \u00b7 " + esc(row[2]) + "%" : "-") + '</span>' +
        '<span style="flex:2.2;text-align:right;color:' + (row[6] < 0 ? "#ff8b8b" : "#77f37b") + '">' + (row[5] != null ? "\u20B9" + esc(row[5]) + " \u00b7 \u0394" + esc(row[7]) + " \u00b7 \u0398" + esc(row[8]) + " \u00b7 " + esc(row[6]) + "%" : "-") + '</span></div>';
    });
    return h;
  }

  function render(box) {
    var h = '<div class="note" style="margin-top:8px">' + esc(D.updated) + ' EOD data \u00b7 216 F&O stocks+index \u00b7 IV Black-Scholes se nikla hai (market close se). <b>Indicative hai, live nahi.</b> Deep ITM strikes me IV ajeeb dikh sakta hai.</div>';
    h += '<input id="grQ" placeholder="\uD83D\uDD0D stock/index likho (e.g. NIFTY, RELIANCE, BANKNIFTY)" style="width:100%;box-sizing:border-box;margin-top:8px;padding:8px 10px;border-radius:9px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:13px">';
    h += '<div id="grChain" style="margin-top:6px"></div>';
    h += '<div style="margin-top:12px;padding:8px 12px;border-radius:10px;background:rgba(240,180,41,.08);border:1px solid rgba(240,180,41,.35)">' +
      '<div style="font-size:13px;font-weight:700">\uD83E\uDCA1 LTP CALCULATOR \u2014 option ka sahi price nikalo (Black-Scholes)</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:6px">' +
      ['grS|Spot', 'grK|Strike', 'grD|Din', 'grIV|IV %', 'grR|Rate %'].map(function (x) {
        var p = x.split("|");
        return '<input id="' + p[0] + '" placeholder="' + p[1] + '" inputmode="decimal" style="width:74px;padding:6px 8px;border-radius:8px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:12px">';
      }).join("") +
      '<select id="grT" style="padding:6px;border-radius:8px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:12px"><option value="c">CE</option><option value="p">PE</option></select>' +
      '<button id="grGo" style="padding:6px 12px;border-radius:8px;border:1px solid rgba(240,180,41,.6);background:rgba(240,180,41,.2);color:#fff;font-size:12px;font-weight:700">CALC</button></div>' +
      '<div id="grOut" style="margin-top:6px;font-size:13px"></div></div>';
    box.innerHTML = h;
    var ch = document.getElementById("grChain");
    var u = D.u[CUR]; if (u) ch.innerHTML = chain(u, EI);
    document.getElementById("grGo").addEventListener("click", calcBox);
    Array.prototype.forEach.call(["grS", "grK", "grD", "grIV"], function (id) {
      document.getElementById(id).addEventListener("keydown", function (e) { if (e.key === "Enter") calcBox(); });
    });
    document.getElementById("grQ").addEventListener("input", function () {
      var v = this.value.trim().toUpperCase();
      if (!v) return;
      var hits = Object.keys(D.u).filter(function (k) { return k.indexOf(v) === 0; });
      if (!hits.length) hits = Object.keys(D.u).filter(function (k) { return k.indexOf(v) > -1; });
      if (hits.length) { CUR = hits[0]; EI = 0; document.getElementById("grChain").innerHTML = chain(D.u[CUR], EI); bind(); }
    });
    function bind() {
      Array.prototype.forEach.call(box.querySelectorAll(".grExp"), function (b) {
        b.addEventListener("click", function () { EI = +this.getAttribute("data-ei"); document.getElementById("grChain").innerHTML = chain(D.u[CUR], EI); bind(); });
      });
    }
    bind();
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83E\uDDEE OPTION GREEKS</b> <span style="font-size:11px;opacity:.65">Delta \u00b7 Gamma \u00b7 Theta \u00b7 Vega \u00b7 LTP calc</span></summary>' +
      '<div id="grBody" class="note" style="margin-top:8px">loading greeks...</div>';
    fetch("data/greeks.json").then(function (r) { return r.json(); }).then(function (d) {
      D = d; render(document.getElementById("grBody"));
    }).catch(function () {
      var b = document.getElementById("grBody");
      if (b) b.innerHTML = "data load nahi hua \u2014 thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbGreeks")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbGreeks"; c.style.marginTop = "14px";
    var anchor = document.getElementById("mbBP");
    if (anchor && anchor.nextSibling) anchor.parentNode.insertBefore(c, anchor.nextSibling);
    else if (anchor) anchor.parentNode.appendChild(c);
    else {
      var sc = document.getElementById("mbScoreCard");
      if (sc && sc.parentNode) sc.parentNode.insertBefore(c, sc); else sec.appendChild(c);
    }
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
