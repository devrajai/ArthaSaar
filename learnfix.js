/* learnfix.js — Dev's Notebook (Advance.pdf pages 22, 23, 25, 26) in Learn section */
(function () {
  var LN = document.querySelector("#learn");
  if (!LN || document.getElementById("devNoteCard")) return;
  var B = [
    ["Stage Analysis — 20/40 SMA (my rules)", "pages 22",
     "Stage 1: downtrend ke baad consolidation zone banta hai. 20 SMA 40 SMA ko cross karta hai — yahi Stage-1 signal hai. Base ban raha hai. <br>" +
     "Stage 2: BREAKOUT — price 20/40 ke range se upar nikal jaata hai. Candlestick + SKP-2 pattern confirm karke position banao. Ye sabse powerful stage hai — hold karo. <br>" +
     "Stage 3: 20 SMA wapas 40 SMA ke neeche cross — reversal dhongdo, trend ke against mat jao. <br>" +
     "Stage 4: price dono SMA ke neeche — decline phase. Exit / avoid. <br>" +
     "Setup extras: gap dekho, demand-supply zone (V-9/10/13) dekho. Timeframe: swing 4-4 + daily. Stage-4 timing ke liye 13 SMA dekho."],
    ["Stop-Loss Hunting — operator trap", "page 23",
     "Breakout par buyers aate hain, tab operator stoploss hunting karta hai. Operator ek side trap karta hai — lekin jab hum galat side position lete hain to dono side trap. <br>" +
     "Jab SL 3-4 baar hit hota hai, public sochta hai naya breakout aaya — aur bech deta hai. Tab operator thoda price giraake wapas previous level laata hai aur uptrend banata hai. <br>" +
     "Lower timeframe par bahut saare SL traps milte hain. Doji/hammer jaise candle structure padho. <br>" +
     "RULE: mid mein kabhi buy mat karo. 2 attempt mein price upar nahi jaata = exit. Position sirf upper/lower point par banao."],
    ["Big Elephant candle + Change of Polarity", "page 25",
     "Breakout pass wali candle = big elephant — pichhli candles aur unke mixture se kaafi badi candle. 20% technique ke saath dekho. <br>" +
     "Change of Polarity (CoP): jab resistance toot jaata hai, to wahi level aage support ban jaata hai — polarity badal jaati hai."],
    ["Dead Cat Bounce + W pattern", "page 26",
     "20 SMA (15 min) / 20-40 SMA ke saath: sharp drop ke baad jo chhota bounce aata hai wo dead cat bounce hai — PEHLA BOUNCE DANGER hai, asli U-turn nahi. <br>" +
     "Seller us bounce par apni position cover karke profit book karta hai — us level par buy mat karo. <br>" +
     "Asli U-turn: support par pehle consolidation ho, phir 20 SMA ke paas W pattern bane — tabhi buying zone. <br>" +
     "Top point par panic sell hota hai; bottom zone hold hota hai. Buyer lambe time tak position hold kar sakta hai."]
  ];
  var el = document.getElementById("eduBox");
  var card = document.createElement("div");
  card.className = "card"; card.id = "devNoteCard";
  card.innerHTML = '<div class="subhead">My Notebook — own rules (Advance.pdf)</div>' +
    B.map(function (x) {
      return '<details style="margin:8px 0"><summary><b>' + esc(x[0]) + '</b> <span class="footer-note">— ' + esc(x[1]) + '</span></summary><div class="note" style="margin-top:6px">' + x[2] + '</div></details>';
    }).join("") +
    '<div class="footer-note">my handwritten rules, digital version · educational only — not signals</div>';
  if (el && el.nextSibling) LN.insertBefore(card, el.nextSibling);
  else LN.appendChild(card);
})();
