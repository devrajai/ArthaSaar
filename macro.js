/* macro.js - Macro Pulse card (oil/dollar/10Y/rupee/gold + FII streak + verdict) in Global section */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function fmt(v, pre, post) { return v == null ? "-" : pre + v + post; }
  function render(d) {
    var t = d.today || {}, sc = d.score || 0;
    var col = sc <= -4 ? "#ff6b6b" : sc <= -2 ? "#ffb84d" : sc <= 0 ? "#9fb4c7" : "#77f37b";
    var rows = [
      ["Crude Oil (WTI)", fmt(t.crude, "$", "")],
      ["Dollar Index (DXY)", fmt(t.dxy, "", "")],
      ["US 10Y Yield", fmt(t.us10y, "", "%")],
      ["Rupee (USDINR)", fmt(t.usdinr, "Rs ", "")],
      ["Gold", fmt(t.gold, "$", "")],
      ["FII aaj", t.fii_net_cr == null ? "-" : "Rs " + t.fii_net_cr + " cr " + (t.fii_net_cr < 0 ? "(becha)" : "(khareeda)")]
    ];
    var sig = (d.signals || []).map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("");
    var streak = d.streak_fii_sell_days || 0;
    var streakLine = streak >= 3 ? '<div class="note" style="margin-top:8px">FII <b>' + streak + ' din se lagatar bech rahe hain</b></div>' : "";
    var box = document.getElementById("macroPulseCard");
    if (!box) return;
    box.innerHTML =
      '<div class="subhead">Macro Pulse - video wala "3 cheezein" (oil, dollar, FII)</div>' +
      '<div class="note" style="margin:8px 0"><b style="font-size:15px;color:' + col + '">Verdict: ' + esc(d.verdict || "-") + '</b> <span style="opacity:.7">(score ' + sc + '/10)</span></div>' +
      rows.map(function (r) { return '<div class="note" style="display:flex;justify-content:space-between"><span>' + r[0] + '</span><b>' + r[1] + '</b></div>'; }).join("") +
      streakLine +
      (sig ? '<div class="note" style="margin-top:8px"><b>Kyun:</b><ul style="margin:4px 0 0 16px;font-size:12px;line-height:1.6">' + sig + "</ul></div>" : "") +
      '<div class="footer-note">roz 7:05 AM update - 5-din ke change se signals nikalte hain</div>';
  }
  function mount() {
    var sec = document.querySelector("section#global");
    if (!sec || document.getElementById("macroPulseCard")) return;
    var card = document.createElement("div");
    card.className = "card"; card.id = "macroPulseCard";
    card.innerHTML = '<div class="subhead">Macro Pulse</div><div class="note"></div>';
    sec.appendChild(card);
    fetch("data/macro.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(render).catch(function () {
      var b = document.getElementById("macroPulseCard");
      if (b) b.innerHTML = '<div class="subhead">Macro Pulse</div><div class="note">data abhi nahi mila.</div>';
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
