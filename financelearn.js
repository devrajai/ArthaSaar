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
    ["10. Books (beginner se pro)", "Psychology of Money (mindset), Let's Talk Money (Indians ke liye practical), Rich Dad Poor Dad (assets vs liabilities), The Intelligent Investor (value investing bible), Coffee Can Investing (India)."],
    ["11. Inflation - chupi chori", "Har saal cheezein 4-6% mehngi ho jaati hain - matlab bina invest kiye paisa girta hai. 10 saal pehle ki 100 wali thali aaj 180 ki. Isliye FD-safe soch asal me paisa gawaye hue hai. Real return = return - inflation."],
    ["12. Diversification - ande aur tokri", "Sab ande ek tokri me mat rakho. 1 stock girne se poora paisa nahi jana chahiye. 8-12 alag sector ke stocks ya index hi kaafi hai. Zyada diversify = market jaisa hi return, faayda nahi."],
    ["13. Asset Allocation - 100 minus age", "Paisa kahan batna hai: equity (growth), debt (safety), gold (crisis), cash (opportunity). Simple rule: 100 - umar = equity %. 25 saal ka = 75% equity. Har saal ek baar rebalance karo - winner becho, loser kharido."],
    ["14. Business Models - company kaise kamati hai", "3 type: B2C (Netflix - directly logo se), B2B (auto parts company - company se), subscription (har mahine repeat paisa). Best model = recurring revenue + switching cost (customer ja hi na paaye) + brand moat."],
    ["15. Financial Modeling - excel se samajh", "Company ke future numbers ka anuman: sales kitna badhega, margin kya hoga, profit kya banega. 3 drivers: growth, margin, capital. Analyst isi se target price banata hai. Site ka Bullish Scanner isi logic ka simple version hai."],
    ["16. Mutual Funds - active vs index", "Index fund = poora Nifty, fees 0.2% - market ka return pakka. Active fund = manager kharidta hai, fees 1.5-2% - market ko harana padta hai, aur 80% 10 saal me nahi hara paate. Default: index. Site ke MF Verdict me funds compare karo."],
    ["17. Emergency Fund & Insurance - pehle safety", "Pehle 6 mahine ka kharcha liquid me rakho (FD/liquid fund). Term insurance (10x saal ki kamai) + health insurance - dono zaroori, investment nahi hai, protection hai. Ye na ho to ek bimari poora plan barbaad."],
    ["18. Tax basics - kitna kaat raha hai", "Slab system: kamai jitni zyada, tax utna zyada. Saving: 80C (1.5L - PPF, ELSS, EPF), 80D (health insurance). STCG 20% < 1 saal, LTCG 12.5% > 1 saal stocks. Tax saving ka best saal-aaha tool: hold 1 saal+. Site ka Tax Calculator try karo."],
    ["19. Credit Score - CIBIL 300-900", "Loan lena ho (ghar, gaadi) to ye report card hai. 750+ = loan aasani se, best rate. Girta hai: late payment, bahut cards, high utilization. Badhta hai: time pe EMI, pura bill, kam credit use."],
    ["20. Market Cycles - bull, bear, recovery", "Bull (upar, greed), Bear (neeche, dar), Recovery (darr me shuru hoti hai). History: har bear ke baad naya high aaya hai - par waqt lagta hai. Rule: market timing nahi, time in market."],
    ["21. GDP & Macro - economy ka report card", "GDP = desh ki total kamai. Badhta hai to company profit badhta hai to stock badta hai. Repo rate, inflation, USD-INR - teeno site ke Macro card me hain. Macro direction pata ho to galti kam hoti hai."],
    ["22. Retirement - PPF, EPF, NPS", "EPF (naukri wala, auto), PPF (7% tax-free, 15 saal), NPS (market linked, extra 50k tax saving). Rule: jitni jaldi shuru, utna compounding ka jaadu. 25 saal me 5k SIP = 60 pe ~1.5 Cr (12% pe)."]
  ];
  function build(card) {
    var h = '<div class="note" style="margin-top:8px">Naye members ke liye - trading se pehle ye 22 concepts aane chahiye. Seedha Hinglish, zero jargon. (samriddhisdiary series se inspire, apne words me)</div>';
    T.forEach(function (t) {
      h += '<details style="margin-top:8px"><summary style="cursor:pointer;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:14px"><b>' + t[0] + '</b></summary>' +
        '<div class="note" style="padding:6px 14px 2px 14px">' + t[1] + '</div></details>';
    });
    card.innerHTML = '<div class="subhead">Finance Basics - 22 Concepts (series)</div>' + h;
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
