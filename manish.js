/* manish.js - Manish GTI Playbook: Learn section mein podcast rules ka collapsible card */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var sec = document.querySelector("section#learn");
  if (!sec || document.getElementById("manishCard")) return;
  var d = document.createElement("details");
  d.className = "gl"; d.id = "manishCard"; d.style.marginTop = "12px";
  var items = [
    ["Candle types (GTI)", "Blue = badi KHARIDI (institutional buying) · Black = badi BECHDI (institutional selling) · Yellow = operator candle (agle 1.5 ghante trade MAT karo, phir range ka breakout) · Bubble = whale/liquidity volume. Candle ka COLOR kabhi mat dekho - sirf STRUCTURE dekho."],
    ["Zones - GTI ka core", "Do buying zone neeche, do selling zone upar, beech mein battlefield. Buying zone mein sirf BUY, selling zone mein sirf SELL. Target = opposite zone (zone-to-zone). SL = zone ke paar 3-min CANDLE CLOSE se (wick nahi)."],
    ["Probability ladder", "1 confirmation = 20% se kam · 3 = ~70% · 4 = 78%+ · 5-6 = 98% tak. Stack: GTI zones (4H+D+W) + whale pattern + institutional activity + RSI sabse aakhir mein."],
    ["6 Trap types", "1) Bull trend ke top par BB na chhue candle - uske neeche breakdown = reversal. 2) Green candle par negative delta. 3) Higher-high fake (naya high banake free-fall). 4) Chart pattern jahan 70-80% log loss karte hain. 5) Green candle bearish structure. 6) RSI divergence KE AGAINST trend - sabse zyada paisa YAHIN hai."],
    ["CAMCD - 5 phases (F&O)", "Compression = directional trading (whale enter karte hain) · Accumulation = trap trading · Manipulation = sabse profitable (trap ke reversal par) · Correction · Distribution. Nifty compression se minimum 200-300 points, BankNifty/BTC se 1000 points move aata hai. 80% din sideways hote hain - directional sirf 4-5 din/mahina."],
    ["Entry rules", "3-min chart (Guru ka number). Compression mein: golden line ke upar + blue/red zone merge + blue candle + subah ki pehli 3-min candle ka HIGH break = BUY. W pattern support par = buy, M pattern resistance par = sell (par 8-9 me se 10 entry buying hoti hai). Pehli candle ka wait nahi karna - seedha entry."],
    ["Capital rules (option buying)", "Trade sirf expiry days par. 1 strike OTM hi (ATM/ITM nahi). Sirf index, overnight nahi. Account ka sirf 10% (35k) per trade. Minimum 25 points capture, max 35 points SL (freak trade se bachne ke liye system SL). 2 trades/day max. Option selling = capital ka max 33%."],
    ["300-point theory", "Nifty 300-point blocks mein chalti hai - har 300 par bade players ki positions hoti hain. Swing se 300-grid banao + Fibonacci upar. Entry-sync: level 23,450 hai par price 23,382 hai? MAT kharido - exact level ka wait karo. Whales kabhi ek shot mein nahi chalate - blocks ke beech ping-pong."],
    ["Institutional candle 50%", "Bada black candle (high-volume selling) banega - jab price us candle ke 50% tak pahunchega, market GIREGA. Wapas blue candle ka area aaye to buy-on-dip."],
    ["Panchak calendar (75% win rate)", "Panchak ke 5 din correction aata hai (~500 points). Agar bottom par ho to up-correction, mid-range par fake breakout phir girna, top par 500-point fall. 2026: 3 Oct, 27 Nov-1 Dec panchak. Amavasya: 21 Oct, 20 Nov, 19 Dec. April aur August option buyers ke liye worst months."],
    ["Operator hierarchy", "Whales (10,000+ cr, 1000-pt targets) > Sharks (institutions, SL-hunting karte hain ~200 points) > Stags (algos, whale positions jaante hain) > Pigs (retail - breakout karte hain, slaughter hote hain). Rule: jis din DI bade buyer hain, AGLE DIN SL hunting pakka aayegi. Whale tabhi enter karta hai jab koi phansa ho."]
  ];
  d.innerHTML = '<summary><b>Manish GTI Playbook - podcast se saare rules (free mein jo 35k ka course tha)</b></summary>' +
    '<div class="note" style="margin-top:8px">Manish (GTI creator) ke 10 podcasts se extract kiye gaye rules. GTI = signal nahi, DATA READING hai. Ye sab GTI v3 indicator + website GTI Zones mein already code ho chuka hai.</div>' +
    items.map(function (x) {
      return '<details style="margin:6px 0"><summary><b>' + esc(x[0]) + "</b></summary><div class=\"note\" style=\"margin-top:5px\">" + esc(x[1]) + "</div></details>";
    }).join("") +
    '<div class="footer-note">source: Manish ke podcasts · GTI v3 indicator file bhi available hai</div>';
  var eb = document.getElementById("eduBox");
  if (eb && eb.previousSibling) sec.insertBefore(d, eb); else sec.appendChild(d);
})();
