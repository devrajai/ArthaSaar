/* economypulse.js - Economy Pulse: 15 indicators in News section (top, above News Volume) */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function mbars(m) {
    if (!m || !m.length) return "";
    var mx = 0; m.forEach(function (x) { mx = Math.max(mx, Math.abs(x.v)); });
    if (!mx) return "";
    var h = '<div style="margin-top:8px">' +
      '<div style="display:flex;align-items:stretch;gap:3px;height:46px">';
    m.forEach(function (x) {
      var bh = Math.max(2, Math.round(20 * Math.abs(x.v) / mx));
      var pos = x.v >= 0;
      var tip = esc(x.k) + ": " + (x.v > 0 ? "+" : "") + Math.round(x.v).toLocaleString("en-IN") + " cr";
      var up = pos ? '<div style="width:100%;height:' + bh + 'px;border-radius:2px 2px 0 0;background:#77f37b"></div>' : '<div style="flex:1"></div>';
      var dn = pos ? '<div style="flex:1"></div>' : '<div style="width:100%;height:' + bh + 'px;border-radius:0 0 2px 2px;background:#ff8b8b"></div>';
      h += '<div title="' + tip + '" style="flex:1;display:flex;flex-direction:column">' +
        '<div style="flex:1;display:flex;align-items:flex-end">' + up + '</div>' +
        '<div style="height:1px;background:rgba(255,255,255,.3)"></div>' +
        '<div style="flex:1">' + dn + '</div></div>';
    });
    h += '</div><div style="display:flex;gap:3px;margin-top:2px">' +
      m.map(function (x) { return '<div style="flex:1;text-align:center;font-size:9px;opacity:.55">' + esc(x.k) + '</div>'; }).join("") + '</div></div>';
    return h;
  }

  function row(i) {
    var suffix = i.noYoy ? "" : " YoY";
    var up = (i.yoy || "").indexOf("-") < 0;
    var yoyCol = i.yoy === "\u2014" || !i.yoy ? "var(--dim)" : (up ? "#77f37b" : "#ff8b8b");
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<span style="font-size:16px">' + esc(i.icon) + '</span><b>' + esc(i.name) + "</b>" +
      '<span style="margin-left:auto;font-weight:700;font-size:14px;color:rgba(240,180,41,.95)">' + esc(i.val) + "</span>" +
      '<span style="font-size:11.5px;font-weight:700;color:' + yoyCol + '">' + esc(i.yoy || "") + suffix + "</span></summary>" +
      '<div style="padding:6px 14px 10px 14px">' +
      '<div style="font-size:12px;opacity:.8;line-height:1.5">' + esc(i.sub) + "</div>" +
      mbars(i.m) +
      '<div class="note" style="margin-top:7px"><b style="color:rgba(240,180,41,.9)">Kyun:</b> ' + esc(i.why) + "</div>" +
      '<div class="note" style="margin-top:4px"><b style="color:#77f37b">Stock impact:</b> ' + esc(i.impact) + "</div>" +
      '<div class="note" style="margin-top:4px;opacity:.55">' + esc(i.date) + " \u00b7 " + esc(i.src) + "</div>";
    (i.hl || []).forEach(function (x) {
      h += '<div style="font-size:12px;line-height:1.45;margin-top:5px;opacity:.8"><span style="opacity:.5">' + esc(x.d) + " \u00b7 " + esc(x.s) + "</span> \u2014 " + esc(x.t) + "</div>";
    });
    h += "</div></details>";
    return h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83C\uDDEE\uD83C\uDDF3 ECONOMY PULSE</b></summary>' +
      '<div id="epBody" class="note" style="margin-top:8px"></div>';
    fetch("data/economy-pulse.json").then(function (r) { return r.json(); }).then(function (d) {
      var h = '<div class="note" style="margin-top:8px">Govt data se economy ka asli haal - sab green to economy strong, girne lage to dhyan. Figures verified (monthly releases), headlines roz auto-update. Tap = detail + stock impact + FII monthly bars. (indicative, advice nahi)</div>';
      (d.ind || []).forEach(function (i) { h += row(i); });
      h += '<div class="note" style="margin-top:8px;opacity:.55">' + esc(d.updated || "") + "</div>";
      document.getElementById("epBody").innerHTML = h;
    }).catch(function () {
      var b = document.getElementById("epBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#news");
    if (!sec || document.getElementById("mbEconPulse")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbEconPulse"; c.style.marginTop = "14px";
    var ref = document.getElementById("mbNewsVol") || document.getElementById("newsBox");
    if (ref) sec.insertBefore(c, ref); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
