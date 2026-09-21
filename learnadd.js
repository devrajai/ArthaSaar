/* learnadd.js — Learn mein naye tools ka guide (Smart Brain + MF Tracker + more) */
(function () {
  var sec = document.querySelector("section#learn");
  if (!sec) return;
  var card = document.createElement("div");
  card.className = "card";
  card.id = "newToolsGuide";
  card.style.marginTop = "12px";
  card.innerHTML =
    '<div class="subhead">Naye Tools — kaise use karein</div>' +
    '<div class="note" style="margin-top:8px"><b>🧠 Smart Brain</b> — roz raat 8:55 baje apne aap update hota hai.<br>' +
    "· <b>Kal ka Guess</b>: market ka mood 0-100 (breadth + FII/DII + TimesFM). 55+ = bull side, 45- = weak.<br>" +
    "· <b>Confluence</b>: har stock ka score — AI + EMA200 + RSI + OI sab agree karein to strong signal. +60 se upar ya -60 se neeche wale dekho.<br>" +
    "· <b>Result Radar</b>: kiski board meeting / result aa raha hai.<br>" +
    "· <b>52W Radar</b>: naye highs/lows + kaun market se tez bhaaga (RS).</div>" +
    '<div class="note" style="margin-top:10px"><b>📊 MF Tracker</b> — AMFI ka free data, saare funds daily.<br>' +
    "· Naam ya code likho (jaise bluechip) → fund par tap → NAV, day change, 1Y/3Y return + chart.<br>" +
    "· <b>Add to My MF</b> se apne holdings track karo (units daalo) — total value + P&L.<br>" +
    "· <b>SIP Calculator</b>: monthly amount, saal, return % → kitna banega.<br>" +
    "· Naya password system: har din ka password alag — raat 12 baje apne aap badal jaata hai.</div>" +
    '<div class="note" style="margin-top:10px"><b>💼 Portfolio Night Report</b> — Portfolio section mein aaj ka P&L, kaun diya/liya, aur 90-din value graph (roz khologe to banega).</div>' +
    '<div class="note" style="margin-top:10px"><b>📖 Rules reminder</b> — signals final nahi hote. Confluence score dekho, phir Company Card se fundamentals check karo, stop-loss ke saath hi trade karo. Ye saara data free EOD sources se hai — din bhar ka data shaam ko aata hai.</div>';
  var f = sec.querySelector(".card");
  if (f) sec.insertBefore(card, f); else sec.appendChild(card);
})();
