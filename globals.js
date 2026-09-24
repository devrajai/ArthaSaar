/* globals.js - GLOBAL RADAR (Dev's Bloomberg): duniya ke indices+commodities EOD + Global->India correlation engine. #global */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var D = null;

  function pill(v) {
    var c = v > 0 ? "#77f37b" : (v < 0 ? "#ff8b8b" : "#ccc");
    return "<b style='color:" + c + "'>" + (v > 0 ? "+" : "") + esc(v) + "%</b>";
  }
  function sparkline(cl) {
    if (!cl || cl.length < 2) return "";
    var mn = Math.min.apply(null, cl), mx = Math.max.apply(null, cl);
    var pts = cl.map(function (c, i) { return (i / (cl.length - 1)) * 70 + "," + (18 - (c - mn) / (mx - mn || 1) * 16); }).join(" ");
    var up = cl[cl.length - 1] >= cl[0];
    return "<svg width='70' height='20' viewBox='0 0 70 20' style='flex:0 0 70px'><polyline points='" + pts + "' fill='none' stroke='" + (up ? "#77f37b" : "#ff8b8b") + "' stroke-width='1.4'/></svg>";
  }
  function row2(x) {
    return "<div style='display:flex;align-items:center;gap:8px;padding:7px 4px;margin-top:3px;border-radius:8px;border:1px solid rgba(255,255,255,.07)'>" +
      "<span style='flex:1.4;font-weight:600;font-size:12.5px'>" + esc(x.n) + "</span>" + sparkline(x.sp) +
      "<span style='flex:1;text-align:right;font-size:12px'>" + pill(x.d1) + "</span>" +
      "<span style='flex:1;text-align:right;font-size:11px' title='1 month'>" + pill(x.m1) + "</span>" +
      "</div>";
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(96,165,250,.13);border:1px solid rgba(96,165,250,.5);font-size:14.5px;text-align:center"><b style="color:rgba(125,180,255,.95)">\uD83C\uDF0D GLOBAL RADAR</b> <span style="font-size:11px;opacity:.65">world indices \u00b7 commodities \u00b7 India asar</span></summary>' +
      '<div id="glBody" class="note" style="margin-top:8px">loading world...</div>';
    fetch("data/world.json").then(function (r) { return r.json(); }).then(function (d) {
      D = d;
      var b = document.getElementById("glBody");
      var h = '<div class="note" style="margin-top:8px">' + esc(d.updated) + ' EOD \u00b7 Yahoo Finance free data \u00b7 <b>market band hone ke baad ka analysis hai, live nahi</b></div>';
      h += '<div style="font-size:12px;font-weight:700;margin-top:10px;opacity:.8">\uD83C\uDF0F WORLD INDICES</div>';
      h += '<div style="display:flex;font-size:10px;opacity:.55;padding:0 4px;margin-top:4px"><span style="flex:1.4">Market</span><span style="flex:70px 0 70px"></span><span style="flex:1;text-align:right">Aaj</span><span style="flex:1;text-align:right">1 mah</span></div>';
      d.idx.forEach(function (x) { h += row2(x); });
      h += '<div style="font-size:12px;font-weight:700;margin-top:12px;opacity:.8">\uD83D\uDD70 COMMODITIES + FX</div>';
      d.cmd.forEach(function (x) { h += row2(x); });
      h += '<div style="margin-top:12px;padding:8px 12px;border-radius:10px;background:rgba(240,180,41,.08);border:1px solid rgba(240,180,41,.35)">' +
        '<div style="font-size:13px;font-weight:700">\uD83E\uDED GLOBAL\u2192INDIA ENGINE (90 din ka data)</div>' +
        '<div style="font-size:11px;opacity:.7;margin-top:3px">"Aaj wahan girra, kal India pe kya asar?" \u2014 next-day lag correlation, 90 din ke EOD closes se</div>';
      var seen = {};
      d.corr.slice(0, 6).forEach(function (c) {
        if (seen[c.g]) return; seen[c.g] = 1;
        h += '<div style="margin-top:6px;font-size:12px">\u2022 <b>' + esc(c.g) + '</b> \u2192 ' + esc(c.i) + ' kal: <b style="color:' + (c.l > 0 ? "#77f37b" : "#ff8b8b") + '">' + (c.l > 0 ? "+" : "") + esc(c.l) + "</b> correlation</div>";
      });
      var sk = d.shock["Nasdaq"] || d.shock["S&P 500"];
      if (sk) {
        var key = d.shock["Nasdaq"] ? "Nasdaq" : "S&P 500";
        h += '<div style="margin-top:8px;font-size:12px;padding:6px 8px;border-radius:8px;background:rgba(255,80,80,.08);border:1px solid rgba(255,80,80,.25)">\uD83D\uDD25 <b>' + key + ' 1%+ gira to:</b> NIFTY next day avg ' + (sk.avg > 0 ? "+" : "") + '<b>' + esc(sk.avg) + "%</b> (" + esc(sk.n) + " baar me " + esc(sk.up) + " baar green) \u2014 <i>pattern hai, guarantee nahi</i></div>";
      }
      h += '<div style="font-size:10.5px;opacity:.6;margin-top:6px">Correlation -1 to +1: 0.2+ = halka asar, 0.4+ = strong. War/big event me ye badalta rehta hai.</div></div>';
      b.innerHTML = h;
    }).catch(function () {
      var b = document.getElementById("glBody");
      if (b) b.innerHTML = "data load nahi hua \u2014 thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#global");
    if (!sec || document.getElementById("mbGlobal")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbGlobal"; c.style.marginTop = "14px";
    var h2 = sec.querySelector("h2");
    if (h2 && h2.nextSibling) { sec.insertBefore(c, h2.nextSibling); }
    else { sec.appendChild(c); }
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
