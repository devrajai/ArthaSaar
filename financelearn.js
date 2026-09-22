/* financelearn.js - Finance Basics series (Learn section) - concepts apne words mein */
(function () {
  var T = [
    ["1. Compounding - 8th wonder", "Paisa ka paisa ka paisa. 10% saal pe 1L = 10 saal me 2.6L, 20 saal me 6.7L. Dher late lagta hai phir achanak bada dikhta hai. SIP isi kaam aati hai. Shuru karne ka best din: aaj."],
    ["2. Time Value of Money", "Aaj ka 100 rupya kal ke 100 se zyada hai - inflation. Isliye FD me pada paisa asal me girta hai (6% FD - 5% inflation = sirf 1%). Return hamesha inflation ke baad dekho (real return)."],
    ["3. Risk vs Return", "Zyada return chahiye to zyada risk lena padega - jitna upar utna niche girna. Lekin samjhdaari: sirf wo risk lo jise samajhte ho. Nifty 10 saal me ~12% deta hai with drawdown - us se zyada chahiye to stock/option ka risk."],
    ["4. Financial Statements - 3 statements", "P&L (kamaai-kharcha = profit), Balance Sheet (kya hai kya udhaar), Cash Flow (asli paisa aaya gaya). Rule: Profit opinion hai, Cash fact. Jo company profit dikhati hai par cash nahi - bach ke."],
    ["5. Ratios - PE, PB, ROE, ROCE", "PE = price / profit per share (kitna mehnga). PB = price / book value. ROE = shareholders ke paisa pe kitna kamaya (15%+ accha). ROCE = poore business pe kitna kamaya. Rule: kam PE + high ROE = sundar combo."],
    ["6. Debt (D/E) - accha ya bura", "Debt se business tez badhta hai but musibat me doobta hai. D/E 2x se zyada = dhyan. Interest coverage kam = khatra. Best: company jo bina udhaar 20%+ ROE de."],
    ["7. Banks aur RBI - repo, CRR, SLR", "Repo rate = RBI se udhaar ki bhaari. Repo badha to bank loan mehnga - market ko pasand nahi. CRR/SLR = banks ko RBI ke paas rakhna padta hai. Repo cut cycle = market ka bull run ka khaana."],
    ["8. Valuation basics", "Company ka asli mol kitna? Methods: DCF (future cash aaj ke paise me), Relative (peers ke PE se), DDM. Simple rule: achhi company bhi mehngi ho sakti hai - price hi return decide karta hai."],
    ["9. Hedging - insurance of trades", "Risk ko transfer karna. Stock hold hai to PUT kharid ke neeche ka risk bech do. Hedge fund = dusron ka paisa manage kar alag-alag strategies se. Normal trader: position sizing hi sabse bada hedge hai."],
    ["10. Books (beginner se pro)", "Psychology of Money (mindset), Let's Talk Money (Indians ke liye practical), Rich Dad Poor Dad (assets vs liabilities), The Intelligent Investor (value investing bible), Coffee Can Investing (India)."]
  ];
  function build(card) {
    var h = '<div class="note" style="margin-top:8px">Naye members ke liye - trading se pehle ye 10 concepts aane chahiye. Seedha Hinglish, zero jargon.</div>';
    T.forEach(function (t) {
      h += '<details style="margin-top:8px"><summary style="cursor:pointer;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:14px"><b>' + t[0] + '</b></summary>' +
        '<div class="note" style="padding:6px 14px 2px 14px">' + t[1] + '</div></details>';
    });
    card.innerHTML = '<div class="subhead">Finance Basics - 10 Concepts (series)</div>' + h;
  }
  function mount() {
    var sec = document.querySelector("section#learn");
    if (!sec || document.getElementById("mbFinLearn")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbFinLearn"; c.style.marginTop = "14px";
    sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
