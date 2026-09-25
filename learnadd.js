/* learnadd.js - Learn: collapsible cards (tap karke kholo) */
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
    '<div class="note" style="margin-top:10px"><b>📱 Telegram bot</b> - roz ka schedule: 7:00 AM AI Brief, 9:20 AM Market Open, hourly alerts (market hours), 4:00 PM Close, 9:10 PM Daily Digest, Sunday Report Card + IPO digest.</div>' +
    '<div class="note" style="margin-top:10px"><b>📊 MF Tracker</b> - ab kaam karta hai: naam ya code se search, NAV + returns, My MF holdings, SIP calculator.</div>' +
    '<div class="note" style="margin-top:10px"><b>📣 Social Buzz</b> - Reddit se stocks ke social mentions, Daily Digest mein line aati hai.</div>');
  var gd = glCard("newToolsGuide", "Naye Tools - kaise use karein",
    '<div class="note" style="margin-top:8px">📖 <b>ArthaSaar Learning Hub</b> — written in simple English. Educational only, not investment advice. Read in order: Beginner first, then Intermediate, then Advanced.<br>Educational analysis only — not SEBI-registered investment advice.</div>' +
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
