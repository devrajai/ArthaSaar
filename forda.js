/* forda.js - F&O Radar: Max Pain, PCR, futures basis, Long/Short Buildup, Short Covering, Long Unwinding, India VIX, Nifty PE. #dash top */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null;

  function fmtCr(v) {
    if (v >= 100000) return "\u20B9" + (v / 100000).toFixed(2) + " L cr";
    if (v >= 100) return "\u20B9" + Math.round(v) + " cr";
    return "\u20B9" + v.toFixed(1) + " cr";
  }

  function stat(label, val, sub, col) {
    return '<div style="flex:1;min-width:70px;text-align:center;padding:8px 6px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1)">' +
      '<div style="font-size:10px;opacity:.6">' + esc(label) + '</div>' +
      '<div style="font-size:15px;font-weight:700;color:' + (col || "rgba(240,180,41,.95)") + ';margin-top:2px">' + esc(val) + '</div>' +
      (sub ? '<div style="font-size:9.5px;opacity:.55;margin-top:1px">' + esc(sub) + '</div>' : "") + '</div>';
  }

  function grp(title, emoji, col, list, n, desc) {
    if (!list || !list.length) return "";
    var h = '<div style="margin-top:10px;font-size:13px;font-weight:700;color:' + col + '">' + emoji + ' ' + title + ' (' + n + ')</div>' +
      '<div class="note" style="margin-top:3px;font-size:11px;opacity:.7">' + desc + '</div>';
    h += '<details style="margin-top:5px"><summary style="cursor:pointer;padding:7px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13px">top ' + list.length + ' stocks dekho \u25BE</summary><div style="padding:2px 14px 8px 14px">';
    list.forEach(function (x) {
      h += '<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12.5px">' +
        '<b style="min-width:92px">' + esc(x.s) + '</b>' +
        '<span style="min-width:60px;color:' + (x.p >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (x.p > 0 ? "+" : "") + esc(x.p) + '% price</span>' +
        '<span style="min-width:60px;color:' + (x.o >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (x.o > 0 ? "+" : "") + esc(x.o) + '% OI</span>' +
        '<span style="margin-left:auto;opacity:.55;font-size:11px">' + fmtCr(x.v) + '</span></div>';
    });
    h += '</div></details>';
    return h;
  }

  function render(box) {
    var d = DATA;
    var mpCol = "#77f37b", pcrCol = "rgba(240,180,41,.95)";
    if (d.pcr != null) pcrCol = d.pcr >= 1.2 ? "#77f37b" : (d.pcr <= 0.8 ? "#ff8b8b" : "rgba(240,180,41,.95)");
    if (d.max_pain != null && d.spot) mpCol = d.max_pain >= d.spot ? "#77f37b" : "#ff8b8b";
    var h = '<div class="note" style="margin-top:8px">' + esc(d.updated) + ' ka NSE F&O data. EOD analysis - options/futures traders ke liye. (indicative, advice nahi)</div>';
    h += '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">' +
      stat("MAX PAIN", d.max_pain != null ? String(d.max_pain) : "-", (d.spot ? "spot " + d.spot : ""), mpCol) +
      stat("PCR (OI)", d.pcr != null ? String(d.pcr) : "-", d.pcr != null ? (d.pcr >= 1.2 ? "bullish zone" : (d.pcr <= 0.8 ? "bearish zone" : "neutral")) : "", pcrCol) +
      stat("BASIS (fut-spot)", d.basis != null ? (d.basis > 0 ? "+" : "") + d.basis : "-", d.fut_exp ? d.basis_pct + "% " + d.fut_exp : "", d.basis != null ? (d.basis >= 0 ? "#77f37b" : "#ff8b8b") : "") +
      stat("INDIA VIX", d.vix != null ? String(d.vix) : "-", d.vix != null ? (d.vix < 13 ? "shaant" : (d.vix > 18 ? "darr" : "normal")) : "") +
      stat("NIFTY P/E", d.nifty_pe != null ? String(d.nifty_pe) : "-", "22 ke neeche = sasta zone") +
      '</div>';
    h += '<div class="note" style="margin-top:7px;font-size:11.5px;opacity:.8"><b style="color:rgba(240,180,41,.9)">Kaise padhein:</b> Max Pain = jahan expiry tak price jhukne ki sabse zyada chance (option writers wahan kam se kam dete hain). Basis+ (premium) = demand/firangi bullish. PCR 0.88 matlab call writers zyada active.</div>';
    h += grp("LONG BUILDUP", "\uD83D\uDFE2", "#77f37b", d.lb, d.n_lb, "Price \u2191 + OI \u2191 = naya paisa longs aa raha (bullish)");
    h += grp("SHORT BUILDUP", "\uD83D\uDD34", "#ff8b8b", d.sb, d.n_sb, "Price \u2193 + OI \u2191 = naya paisa shorts aa raha (bearish)");
    h += grp("SHORT COVERING", "\uD83D\uDD35", "#9ecbff", d.sc, d.n_sc, "Price \u2191 + OI \u2193 = shorts bhaag rahe (bullish rally)");
    h += grp("LONG UNWINDING", "\uD83D\uDFE0", "#ffb86c", d.lu, d.n_lu, "Price \u2193 + OI \u2193 = longs profit book kar rahe (weakness)");
    box.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83D\uDCCA F&O RADAR</b> <span style="font-size:11px;opacity:.65">max pain \u00b7 PCR \u00b7 basis \u00b7 buildups \u00b7 VIX</span></summary>' +
      '<div id="frBody" class="note" style="margin-top:8px">loading F&O radar...</div>';
    fetch("data/forda.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; render(document.getElementById("frBody"));
    }).catch(function () {
      var b = document.getElementById("frBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#dash");
    if (!sec || document.getElementById("mbForda")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbForda"; c.style.marginTop = "14px";
    var h2 = sec.querySelector("h2");
    if (h2 && h2.parentNode) sec.insertBefore(c, h2.nextSibling); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
