/* var.js - VaR CALCULATOR: portfolio me 95%/99% confidence se max kitna loss ho sakta hai (parametric VaR). #portfolio */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function fmt(n) { return "\u20B9" + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function calc() {
    var val = parseFloat(document.getElementById("vrV").value) || 0;
    var vol = parseFloat(document.getElementById("vrS").value) || 0;
    var days = parseFloat(document.getElementById("vrD").value) || 1;
    if (val <= 0 || vol <= 0) { document.getElementById("vrOut").innerHTML = "<span class='note'>portfolio \u20B9 aur roz ka vol % bharo</span>"; return; }
    var z95 = 1.65, z99 = 2.33;
    var v95 = val * (vol / 100) * z95 * Math.sqrt(days);
    var v99 = val * (vol / 100) * z99 * Math.sqrt(days);
    document.getElementById("vrOut").innerHTML =
      "<b>1-din VaR:</b><br>\u2022 95% confidence: <b style='color:#ff8b8b'>" + fmt(v95) + "</b> <span style='font-size:11px;opacity:.6'>(20 din me 19 din isse zyada loss hona unlikely)</span><br>" +
      "\u2022 99% confidence: <b style='color:#ff5252'>" + fmt(v99) + "</b><br>" +
      (days > 1 ? "<b>" + esc(days) + "-din VaR:</b> 95% = <b>" + fmt(v95) + "</b>, 99% = <b>" + fmt(v99) + "</b><br>" : "") +
      "<div style='font-size:10.5px;opacity:.6;margin-top:4px'>VaR = portfolio \u00D7 roz ka vol \u00D7 z \u00D7 \u221Adin. Yeh normal-din ka risk hai \u2014 <b>crash din me (2008/2020) loss VaR se 2-3x zyada ho sakta hai</b>. Tool hai, advice nahi.</div>";
  }
  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(129,140,248,.12);border:1px solid rgba(129,140,248,.5);font-size:14.5px;text-align:center"><b style="color:#aab4ff">\uD83D\uDCD3 VaR CALCULATOR</b> <span style="font-size:11px;opacity:.65">max kitna loss ho sakta hai?</span></summary>' +
      '<div style="margin-top:8px;padding:10px 12px;border-radius:10px;background:rgba(129,140,248,.07);border:1px solid rgba(129,140,248,.3)">' +
      '<div style="display:flex;flex-wrap:wrap;gap:6px">' +
      '<input id="vrV" placeholder="Portfolio \u20B9 (e.g. 500000)" inputmode="decimal" style="flex:1;min-width:140px;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:12.5px">' +
      '<input id="vrS" placeholder="Roz ka vol % (0.8-3)" inputmode="decimal" style="width:130px;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:12.5px">' +
      '<input id="vrD" placeholder="Din (1-30)" inputmode="decimal" style="width:90px;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:12.5px"></div>' +
      '<div style="display:flex;gap:5px;margin-top:6px;flex-wrap:wrap"><span style="font-size:10.5px;opacity:.6;align-self:center">Vol preset:</span>' +
      ["0.9|Nifty jaisa", "1.5|Balanced", "2.5|Volatile stock", "4|Crypto jaisa"].map(function (x) {
        var p = x.split("|");
        return '<button data-v="' + p[0] + '" class="vrP" style="padding:4px 9px;border-radius:7px;border:1px solid rgba(129,140,248,.4);background:rgba(129,140,248,.12);color:#fff;font-size:11px">' + p[1] + "</button>";
      }).join("") + '<button id="vrGo" style="padding:4px 14px;border-radius:7px;border:1px solid rgba(240,180,41,.6);background:rgba(240,180,41,.2);color:#fff;font-size:11px;font-weight:700">CALC</button></div>' +
      '<div id="vrOut" style="margin-top:8px;font-size:13px" class="note">Portfolio ka value daalo, risk ka sach pata chalega</div></div>';
    var go = document.getElementById("vrGo");
    if (go) go.addEventListener("click", calc);
    ["vrV", "vrS", "vrD"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("keydown", function (e) { if (e.key === "Enter") calc(); });
    });
    Array.prototype.forEach.call(card.querySelectorAll(".vrP"), function (b) {
      b.addEventListener("click", function () { document.getElementById("vrS").value = this.getAttribute("data-v"); calc(); });
    });
  }
  function mount() {
    var sec = document.querySelector("section#portfolio");
    if (!sec || document.getElementById("mbVar")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbVar"; c.style.marginTop = "14px";
    sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
