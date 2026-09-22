/* mbguide.js - Market Brain Guide: how to use everything, login info, updates. #learn */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var SECTIONS = [
    ["Market Today (#dash)", "Movement Analysis - kyun move kar raha hai (sectors, FII/DII, global, news). Market X-Ray - shaam ka deep analysis auto 6 PM: closing picture, sector breadth, FII vs DII, option walls, GTI zone + blood bath level."],
    ["Trade Tools (#tools)", "Calculators (position size, SL, targets), Options Greeks, Operator Radar (delivery % se smart paisa), Dividend calendar, Expiry Day special (NIFTY Tuesday), FII/DII activity, Portfolio tracker (khudke stocks daalo), Stock Deep Charts (PE/ROE/ROCE bars + 13Q profit), Peer Comparison (same industry ke saathi side-by-side)."],
    ["Fundamentals (#fundamentals)", "Bullish Scanner - 500 stocks scored: week/month/year/long-term, F=quality T=technicals, bearish list bhi."],
    ["Mutual Funds (#mf)", "MF Verdict - top funds r1/r3/r5 returns ke saath, SIP calculator bhi."],
    ["GTI (#gti)", "Dev ka apna zone system - SD/WD/WS/SS zones, guide, OI combo. TradingView ke liye GTI v11 Signal Edition (BUY/SELL 6-confirmations)."],
    ["Learn (#learn)", "Finance Basics 10 concepts + ye guide card."]
  ];
  var UPDATES = [
    "22 Sep: Market X-Ray (evening auto-analysis), Peer Comparison, Learn Guide",
    "21-22 Sep: Bullish Scanner, Movement Analysis, FII/DII card, Portfolio tracker, Deep Charts, MF Verdict, Finance Basics, TG Morning Digest 8 AM",
    "21 Sep: PWA + Android APK, Tax Calculator, Muhurat/Budget cards, Trade Tools power pack"
  ];

  function block(title, items, colored) {
    var h = '<div style="font-size:12px;letter-spacing:.6px;opacity:.65;margin-top:14px;font-weight:600">' + title + "</div>";
    items.forEach(function (it) {
      h += '<div style="margin-top:7px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.03);font-size:13px;line-height:1.5' + (colored ? ";border-left:3px solid " + colored : "") + '">' + esc(it) + "</div>";
    });
    return h;
  }

  function mount() {
    var t = document.querySelector("section#learn");
    if (!t || document.getElementById("mbGuide")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbGuide"; c.style.marginTop = "14px";
    t.insertBefore(c, t.firstChild);
    var h = '<div class="subhead">Market Brain Guide (How to use sab kuch)</div>';
    h += block("LOGIN / PASSWORD", [
      "Password din ke hisaab se badalta hai - shaam tak wahi rehta hai. Din me ek baar poochta hai, phir yaad rakhta hai.",
      "Format: Devisbest + number + day. Jaise Monday = Devisbest1Mon, Sunday = Devisbest7Sun.",
      "Logout karne ke liye top par #lock button."
    ], "rgba(240,180,41,.7)");
    SECTIONS.forEach(function (s) {
      h += '<div style="margin-top:14px;padding:9px 13px;border-radius:9px;background:rgba(255,255,255,.03);border-left:3px solid rgba(159,176,196,.5)"><div style="font-size:13px;font-weight:600">' + s[0] + '</div><div style="font-size:12.5px;opacity:.8;margin-top:4px;line-height:1.5">' + esc(s[1]) + "</div></div>";
    });
    h += block("TELEGRAM (kam notifications)", [
      "Morning Digest - 8 AM (FII/DII, GTI zone, top picks, news). Bas itna hi spam - baaki sab website pe jab chaho dekho.",
      "Birthday wishes + important IPO/macro alerts kabhi kabhi."
    ]);
    h += block("MOBILE APP", [
      "Android: market-brain.apk download karo (site par link). iPhone: Safari -> Share -> Add to Home Screen.",
      "App me bhi same password chalta hai."
    ]);
    h += block("LATEST UPDATES", UPDATES, "rgba(119,243,123,.6)");
    h += '<div class="note" style="margin-top:10px;font-size:11.5px;opacity:.55">Market Brain By : Dev Raj with Sarvam Ai. Data free sources se - levels aur bias hai, guarantee nahi. SL hamesha.</div>';
    c.innerHTML = h;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
