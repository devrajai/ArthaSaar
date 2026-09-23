/* economypulse.js - Economy Pulse: 6 govt indicators (GST, Rail, Ports, Auto, EPFO, Power) in Global section */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function row(i) {
    var up = (i.yoy || "").indexOf("-") < 0;
    var yoyCol = i.yoy === "\u2014" || !i.yoy ? "var(--dim)" : (up ? "#77f37b" : "#ff8b8b");
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<span style="font-size:16px">' + esc(i.icon) + '</span><b>' + esc(i.name) + "</b>" +
      '<span style="margin-left:auto;font-weight:700;font-size:14px;color:rgba(240,180,41,.95)">' + esc(i.val) + "</span>" +
      '<span style="font-size:11.5px;font-weight:700;color:' + yoyCol + '">' + esc(i.yoy || "") + " YoY</span></summary>" +
      '<div style="padding:6px 14px 10px 14px">' +
      '<div style="font-size:12px;opacity:.8;line-height:1.5">' + esc(i.sub) + "</div>" +
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
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83C\uDDEE\uD83C\uDDF3 ECONOMY PULSE</b> <span style="font-size:11px;opacity:.65">GST \u00b7 Rail \u00b7 Ports \u00b7 Auto \u00b7 Jobs \u00b7 Power</span></summary>' +
      '<div id="epBody" class="note" style="margin-top:8px">loading economy pulse...</div>';
    fetch("data/economy-pulse.json").then(function (r) { return r.json(); }).then(function (d) {
      var h = '<div class="note" style="margin-top:8px">Govt data se economy ka asli haal - sab green to economy strong, girne lage to dhyan. Figures verified (monthly releases), headlines roz auto-update. Tap = detail + stock impact. (indicative, advice nahi)</div>';
      (d.ind || []).forEach(function (i) { h += row(i); });
      h += '<div class="note" style="margin-top:8px;opacity:.55">' + esc(d.updated || "") + "</div>";
      document.getElementById("epBody").innerHTML = h;
    }).catch(function () {
      var b = document.getElementById("epBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#global");
    if (!sec || document.getElementById("mbEconPulse")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbEconPulse"; c.style.marginTop = "14px";
    sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
