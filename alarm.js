/* alarm.js - CORRECTION ALARM: Market Stress Meter 0-100 (2008/2020-style early warning). #dash */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function col(score) { return score >= 75 ? "#ff5252" : score >= 55 ? "#ffab40" : score >= 30 ? "#ffd54f" : "#77f37b"; }
  function bar(label, v, max, txt) {
    var w = Math.min(100, v / max * 100);
    return "<div style='margin-top:7px'><div style='display:flex;font-size:11px;opacity:.8'><span>" + label + "</span><span style='margin-left:auto'>" + txt + "</span></div>" +
      "<div style='height:5px;border-radius:3px;background:rgba(255,255,255,.08);margin-top:3px'><div style='height:5px;border-radius:3px;width:" + w + "%;background:" + col(100) + "'></div></div></div>";
  }
  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(255,80,80,.12);border:1px solid rgba(255,80,80,.5);font-size:14.5px;text-align:center"><b style="color:#ff8b8b">\uD83D\uDEA8 CORRECTION ALARM</b> <span style="font-size:11px;opacity:.65">Market Stress Meter \u00b7 2008/2020-style warning</span></summary>' +
      '<div id="stBody" class="note" style="margin-top:8px">loading...</div>';
    fetch("data/stress.json").then(function (r) { return r.json(); }).then(function (d) {
      var b = document.getElementById("stBody");
      var c = d.comp || {};
      var h = '<div style="text-align:center;margin-top:10px">' +
        '<div style="font-size:44px;font-weight:800;color:' + col(d.score) + ';line-height:1">' + esc(d.score) + '<span style="font-size:16px;opacity:.5">/100</span></div>' +
        '<div style="font-size:13px;font-weight:700;color:' + col(d.score) + '">' + esc(d.band) + '</div>' +
        '<div style="font-size:10.5px;opacity:.6;margin-top:2px">' + esc(d.u) + ' \u00b7 stress >= 60 pe TG alert milta hai</div></div>';
      if (d.nifty && d.nifty.c) h += '<div style="text-align:center;font-size:11.5px;opacity:.75;margin-top:6px">NIFTY \u20B9' + esc(d.nifty.c) + " \u00b7 200-DMA \u20B9" + esc(d.nifty.dma) + " (" + esc((c.dma || {}).d) + "%)</div>";
      h += '<div style="margin-top:10px;padding:8px 12px;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1)">';
      if (c.dma) h += bar("NIFTY vs 200-DMA \u00b7 " + esc(c.dma.s) + "/30 pts", c.dma.s, 30, (c.dma.d > 0 ? "+" : "") + esc(c.dma.d) + "%");
      if (c.vix) h += bar("VIX (dar) \u00b7 " + esc(c.vix.s) + "/25 pts", c.vix.s, 25, "VIX " + esc(c.vix.v));
      if (c.s4) h += bar("Stage-4 stocks \u00b7 " + esc(c.s4.s) + "/25 pts", c.s4.s, 25, esc(c.s4.p) + "% (" + esc(c.s4.n) + ")");
      if (c.fii) h += bar("FII selling streak \u00b7 " + esc(c.fii.s) + "/20 pts", c.fii.s, 20, esc(c.fii.n) + " din");
      h += '</div><div style="font-size:10.5px;opacity:.6;margin-top:8px">\uD83D\uDDA4 History: 2008 me NIFTY -60% (wapsi ~5 saal), 2020 me -38% (wapsi ~6 mahine). 0-29 normal, 30-54 alert, 55-74 high, 75+ danger. <b>Indicator hai, prediction nahi</b> \u2014 position sizing khud decide karo.</div>';
      b.innerHTML = h;
    }).catch(function () {
      var b = document.getElementById("stBody");
      if (b) b.innerHTML = "data load fail \u2014 refresh karo";
    });
  }
  function mount() {
    var sec = document.querySelector("section#dash");
    if (!sec || document.getElementById("mbAlarm")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbAlarm"; c.style.marginTop = "14px";
    sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
