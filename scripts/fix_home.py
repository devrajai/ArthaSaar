#!/usr/bin/env python3
"""fix_home.py - home tiles -> horizontal chip row (scroll par hide), Learn mein What's New,
Charts option hide (kaam nahi karta tha). One-shot writer script."""
import io, os

# ---------- 1. index.html: homegrid -> horizontal chip row ----------
s = io.open("index.html", encoding="utf-8").read()
if 'id="homeRow"' not in s:
    i = s.find('<div class="homegrid">')
    assert i > 0, "homegrid not found"
    j = s.find("</section>", i)
    assert j > i, "home section end not found"
    chips = [("company", "🏢", "Company Card"), ("dash", "📊", "Dashboard"),
             ("indices", "📈", "Indices"), ("heatmap", "🔥", "Sector Map"),
             ("screener", "🔍", "Screener"), ("fundamentals", "🏢", "Fundamentals"),
             ("mf", "📊", "MF Tracker"), ("deepfund", "💎", "Deep Fund"),
             ("filings", "📄", "Filings"), ("futures", "🧾", "Futures"),
             ("ipo", "🚀", "IPO"), ("ai", "🤖", "AI Forecast"),
             ("aibrain", "🧠", "AI Brain"), ("crypto", "🪙", "Crypto"),
             ("global", "🌍", "Global"), ("news", "📰", "News"),
             ("events", "📅", "Events"), ("portfolio", "💼", "Portfolio"),
             ("learn", "📚", "Learn"), ("studies", "🧪", "Studies"),
             ("mynotes", "📝", "My Notes")]
    parts = ['<div class="hrow" id="homeRow">']
    for h, ic, nm in chips:
        parts.append('<a class="hchip" href="#%s">%s %s</a>' % (h, ic, nm))
    parts.append("</div>\n</section>")
    s = s[:i] + "\n".join(parts) + s[j + len("</section>"):]
    n = s.count("?v=21sep26l")
    s = s.replace("?v=21sep26l", "?v=21sep26m")
    io.open("index.html", "w", encoding="utf-8").write(s)
    print("index.html: homegrid -> hrow (21 chips, no charts) | versions bumped:", n)
else:
    print("index.html: already patched")

# ---------- 2. style.css: hrow/hchip styles ----------
c = io.open("style.css", encoding="utf-8").read()
if ".hrow" not in c:
    c += "\n/* --- home horizontal chip row --- */\n.hrow{display:flex;flex-wrap:nowrap;gap:8px;overflow-x:auto;padding:6px 2px 12px;-webkit-overflow-scrolling:touch;scrollbar-width:none}\n.hrow::-webkit-scrollbar{display:none}\n.hchip{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border-radius:999px;background:var(--glass);border:1px solid var(--border);color:var(--text);text-decoration:none;font-size:13px;font-weight:600;white-space:nowrap}\n.hchip:active{background:var(--glass2);border-color:var(--border2)}\n.hchip:visited{color:var(--text)}\n"
    io.open("style.css", "w", encoding="utf-8").write(c)
    print("style.css: hrow/hchip added")
else:
    print("style.css: already has hrow")

# ---------- 3. homefix.js: scroll par row hide/show ----------
io.open("homefix.js", "w", encoding="utf-8").write(
"""/* homefix.js - home chips row: scroll down par chhupao, up par wapas */
(function () {
  var row = document.querySelector(".hrow");
  if (!row) return;
  var last = 0;
  window.addEventListener("scroll", function () {
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    if (y > last + 8 && y > 80) { row.style.display = "none"; }
    else if (last - y > 8) { row.style.display = ""; }
    last = y;
  }, { passive: true });
})();
""")
print("homefix.js written")

# ---------- 4. learnadd.js: What's New + guide ----------
io.open("learnadd.js", "w", encoding="utf-8").write(
"""/* learnadd.js - Learn: What's New (22 Sep) + naye tools ka guide */
(function () {
  var sec = document.querySelector("section#learn");
  if (!sec) return;
  var card = document.createElement("div");
  card.className = "card";
  card.id = "whatsNewCard";
  card.style.marginTop = "12px";
  card.innerHTML =
    '<div class="subhead">💥 Naya Kya Hai - 22 Sep</div>' +
    '<div class="note" style="margin-top:8px"><b>🧠 AI Brain</b> - 4 naye cards: Market Mood Meter (news sentiment 0-100), Crash Warning System (VIX + FII + breadth ka risk score), TimesFM Report Card (accuracy - 9 Oct se), Sector Rotation.</div>' +
    '<div class="note" style="margin-top:10px"><b>🏆 AI Scores</b> - har stock ko 1-10 score (Technical 60% + Fundamental 40%): RSI, EMA200, MACD, volume + PE, ROE, karza, growth. Roz raat update.</div>' +
    '<div class="note" style="margin-top:10px"><b>💡 Monthly AI Stock Ideas</b> - har mahine 1 tareekh ko Telegram par top 5 stocks: reasons + Entry/Stop/Target + swing ya positional approach.</div>' +
    '<div class="note" style="margin-top:10px"><b>📱 Telegram bot</b> - roz ka schedule: 7:00 AM AI Brief, 9:20 AM Market Open, hourly alerts (market hours), 4:00 PM Close, 9:10 PM Daily Digest, Sunday Report Card + IPO digest. Abhi 5 members.</div>' +
    '<div class="note" style="margin-top:10px"><b>📊 MF Tracker</b> - ab kaam karta hai: naam ya code se search, NAV + returns, My MF holdings, SIP calculator.</div>' +
    '<div class="note" style="margin-top:10px"><b>🏠 Home screen</b> - saare topics ab ek horizontal line mein (left-right scroll karke dekho), page scroll par chhup jaata hai. Charts option hata diya (kaam nahi kar raha tha).</div>' +
    '<div class="note" style="margin-top:10px"><b>📣 Social Buzz</b> - Reddit se stocks ke social mentions, Daily Digest mein line aati hai.</div>';
  var first = sec.querySelector(".card");
  if (first) sec.insertBefore(card, first); else sec.appendChild(card);

  var guide = document.createElement("div");
  guide.className = "card";
  guide.id = "newToolsGuide";
  guide.style.marginTop = "12px";
  guide.innerHTML =
    '<div class="subhead">Naye Tools - kaise use karein</div>' +
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
    '<div class="note" style="margin-top:10px"><b>📖 Rules reminder</b> - signals final nahi hote. Confluence score dekho, Company Card se fundamentals check karo, stop-loss ke saath hi trade karo.</div>';
  if (first) sec.insertBefore(guide, first); else sec.appendChild(guide);
})();
""")
print("learnadd.js rewritten (whats new + guide)")

# ---------- 5. app.js: homefix.js loader mein ----------
a = io.open("app.js", encoding="utf-8").read()
if "homefix.js" not in a:
    assert '"aibrain.js"' in a, "loader anchor missing"
    a = a.replace('"aibrain.js"', '"aibrain.js", "homefix.js"')
    io.open("app.js", "w", encoding="utf-8").write(a)
    print("app.js: homefix.js added to loader")
else:
    print("app.js: already has homefix")
print("ALL DONE")
