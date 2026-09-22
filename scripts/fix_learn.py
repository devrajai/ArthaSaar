#!/usr/bin/env python3
"""fix_learn.py - Learn card: topics 2-row wrap + What's New / Naye Tools collapsible (tap-to-open)."""
import io

# ---------- 1. style.css: learnChips single line -> 2-row wrap ----------
c = io.open("style.css", encoding="utf-8").read()
old_rule = "#learnChips{display:flex;flex-wrap:nowrap;gap:8px;overflow-x:auto;padding:6px 2px 12px;-webkit-overflow-scrolling:touch;scrollbar-width:none}"
new_rule = "#learnChips{display:flex;flex-wrap:wrap;gap:8px;padding:6px 2px 12px}"
if old_rule in c:
    c = c.replace(old_rule, new_rule, 1)
    io.open("style.css", "w", encoding="utf-8").write(c)
    print("style.css: learnChips 2-row wrap")
else:
    print("style.css: rule not found (already patched?)")

# ---------- 2. learnadd.js: collapsible details cards ----------
io.open("learnadd.js", "w", encoding="utf-8").write(
"""/* learnadd.js - Learn: collapsible cards (tap karke kholo) */
(function () {
  var sec = document.querySelector("section#learn");
  if (!sec) return;
  function glCard(id, title, inner) {
    var d = document.createElement("details");
    d.className = "gl";
    d.id = id;
    d.style.marginTop = "12px";
    d.innerHTML = '<summary><b>' + title + '</b></summary>' + inner;
    return d;
  }
  var wn = glCard("whatsNewCard", "💥 Naya Kya Hai - 22 Sep",
    '<div class="note" style="margin-top:8px"><b>🧠 AI Brain</b> - 4 naye cards: Market Mood Meter (news sentiment 0-100), Crash Warning System (VIX + FII + breadth ka risk score), TimesFM Report Card (accuracy - 9 Oct se), Sector Rotation.</div>' +
    '<div class="note" style="margin-top:10px"><b>🏆 AI Scores</b> - har stock ko 1-10 score (Technical 60% + Fundamental 40%): RSI, EMA200, MACD, volume + PE, ROE, karza, growth. Roz raat update.</div>' +
    '<div class="note" style="margin-top:10px"><b>💡 Monthly AI Stock Ideas</b> - har mahine 1 tareekh ko Telegram par top 5 stocks: reasons + Entry/Stop/Target + swing ya positional approach.</div>' +
    '<div class="note" style="margin-top:10px"><b>📱 Telegram bot</b> - roz ka schedule: 7:00 AM AI Brief, 9:20 AM Market Open, hourly alerts (market hours), 4:00 PM Close, 9:10 PM Daily Digest, Sunday Report Card + IPO digest. Abhi 5 members.</div>' +
    '<div class="note" style="margin-top:10px"><b>📊 MF Tracker</b> - ab kaam karta hai: naam ya code se search, NAV + returns, My MF holdings, SIP calculator.</div>' +
    '<div class="note" style="margin-top:10px"><b>📣 Social Buzz</b> - Reddit se stocks ke social mentions, Daily Digest mein line aati hai.</div>');
  var gd = glCard("newToolsGuide", "Naye Tools - kaise use karein",
    '<div class="note" style="margin-top:8px"><b>🧠 Smart Brain</b> - roz raat 8:55 baje update.<br>' +
    '<b>Kal ka Guess</b>: mood 0-100. 55+ = bull side, 45- = weak.<br>' +
    '<b>Confluence</b>: har stock ka score - AI + EMA200 + RSI + OI sab agree karein to strong. +60 ya -60 cross dekho.<br>' +
    '<b>Result Radar</b>: kiski board meeting / result aa raha hai.<br>' +
    '<b>52W Radar</b>: naye highs/lows + RS.</div>' +
    '<div class="note" style="margin-top:10px"><b>📊 MF Tracker</b> - AMFI free data.<br>' +
    'Naam ya code likho (jaise bluechip) - fund par tap: NAV, day change, 1Y/3Y return + chart.<br>' +
    '<b>Add to My MF</b>: apne holdings track karo (units daalo) - total value + P&L.<br>' +
    '<b>SIP Calculator</b>: monthly amount, saal, return % - kitna banega.</div>' +
    '<div class="note" style="margin-top:10px"><b>💼 Portfolio Night Report</b> - aaj ka P&L, kaun diya/liya, 90-din value graph.</div>' +
    '<div class="note" style="margin-top:10px"><b>📖 Rules reminder</b> - signals final nahi hote. Confluence score dekho, Company Card se fundamentals check karo, stop-loss ke saath hi trade karo.</div>');
  var first = sec.querySelector(".card");
  if (first) {
    sec.insertBefore(wn, first);
    sec.insertBefore(gd, wn.nextSibling);
  } else {
    sec.appendChild(wn);
    sec.appendChild(gd);
  }
})();
""")
print("learnadd.js rewritten (collapsible)")

# ---------- 3. index.html version bump ----------
s = io.open("index.html", encoding="utf-8").read()
n = s.count("?v=21sep26n")
s = s.replace("?v=21sep26n", "?v=21sep26o")
io.open("index.html", "w", encoding="utf-8").write(s)
print("index.html version bumped:", n)
print("ALL DONE")
