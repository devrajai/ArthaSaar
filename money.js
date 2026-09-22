/* money.js - Tax Calculator (Indian traders: STCG/LTCG) + charges estimate. #tools mein mount */
(function () {
  function inpt(id, ph, val) {
    return '<input id="' + id + '" placeholder="' + ph + '" value="' + (val || "") + '" style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:14px;margin-top:5px">';
  }
  function getV(id) { var e = document.getElementById(id); return e ? parseFloat(e.value) || 0 : 0; }
  function fmt(n) { return n.toLocaleString("en-IN", { maximumFractionDigits: 0 }); }

  function buildTax(card) {
    card.innerHTML =
      '<div class="subhead">Tax Calculator (STCG / LTCG)</div>' +
      '<div class="note" style="margin-top:8px">Delivery trades - kitna tax + charges lagega</div>' +
      inpt("txQty", "Quantity", "50") + inpt("txBuy", "Buy price", "1000") +
      inpt("txSell", "Sell price", "1150") + inpt("txDays", "Kitne din pakda (holding days)", "200") +
      '<div class="note" id="txOut" style="margin-top:10px">values daalo...</div>' +
      '<div class="note" style="margin-top:8px;font-size:12px;opacity:.75">Rates (Budget 2024 se): STCG 20% (1 saal se kam) | LTCG 12.5% (1.25 lakh exemption ke baad). Intraday / F&O = business income (slab rate), ye nahi.</div>';
    function calc() {
      var q = getV("txQty"), b = getV("txBuy"), s = getV("txSell"), days = getV("txDays");
      if (q <= 0 || b <= 0 || s <= 0) return;
      var inv = q * b, sale = q * s, gain = sale - inv;
      var stt = (inv + sale) * 0.001, brok = (inv + sale) * 0.0012;
      var tax = 0, type = "";
      if (days <= 365) { tax = Math.max(0, gain) * 0.20; type = "STCG (20%)"; }
      else { tax = Math.max(0, gain - 125000) * 0.125; type = "LTCG (12.5%, 1.25L exemption)"; }
      var net = gain - tax - stt - brok;
      var col = net >= 0 ? "#77f37b" : "#ff8b8b";
      document.getElementById("txOut").innerHTML =
        'Invested: <b>Rs ' + fmt(inv) + '</b> | Sale: <b>Rs ' + fmt(sale) + '</b><br>' +
        'Gain: <b style="color:' + (gain >= 0 ? "#77f37b" : "#ff8b8b") + '">Rs ' + fmt(gain) + '</b> (' + type + ')<br>' +
        'Tax: <b>Rs ' + fmt(tax) + '</b> | STT: Rs ' + fmt(stt) + ' | Brokerage ~Rs ' + fmt(brok) + '<br>' +
        '<b style="color:' + col + '">Net profit (sab katne ke baad): Rs ' + fmt(net) + '</b>';
    }
    ["txQty", "txBuy", "txSell", "txDays"].forEach(function (id) {
      var e = document.getElementById(id);
      if (e) e.addEventListener("input", calc);
    });
    calc();
  }

  function mount() {
    var sec = document.querySelector("section#tools");
    if (!sec || document.getElementById("mbTax")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbTax"; c.style.marginTop = "14px";
    sec.appendChild(c);
    try { buildTax(c); } catch (e) { c.innerHTML = '<div class="subhead">Tax Calculator</div>'; }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
