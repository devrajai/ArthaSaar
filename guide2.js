/* guide2.js — "About this site" guide card at top of Learn section */
(function () {
  var LN = document.querySelector("#learn");
  if (!LN || document.getElementById("siteGuideCard")) return;
  var S = [
    ["Company Card", "story · management · growth · results — search koi bhi NSE stock, company ka pura card"],
    ["Dashboard", "market breadth (EMA200 %), FII/DII flows, pre-open movers 9:00-9:15, crypto snapshot, VIX, Nifty PCR + max pain"],
    ["Indices", "139 NSE/BSE indices — price, change, PE, PB, 52-week high/low"],
    ["Sector Map", "aaj ka heatmap — sector-wise green/red, kitna bada move"],
    ["Screener", "2,300+ stocks — RSI, MACD, EMA20/200, volume spike, AI-bullish chip, tier 1/2 filters"],
    ["Fundamentals + Deep Fund", "PE, ROE, ROCE, debt, profit growth — screener.in quality data se weekly"],
    ["Filings", "company results, announcements (BSE/NSE filings)"],
    ["Futures", "F&O contract chains, OI, basis + OI Buildup (long/short buildup)"],
    ["Charts", "TradingView live chart — koi bhi NSE symbol, NIFTY, SENSEX, BTC, GOLD — 1min se daily"],
    ["IPO", "running IPOs, GMP, listing gains"],
    ["AI Forecast", "Google TimesFM 3.0 — Nifty, BankNifty, 80 F&O stocks + BTC: 7d se 3 mahine forecast, confidence %, sector rotation, big movers, accuracy tracker"],
    ["Trade Tools", "GTT-style price planner (agar price X aaye to kya karna), support/resistance levels (phone par save), Chartink quick scanners, Stage Scanner (20/40 rules)"],
    ["Crypto", "top 100 coins — price, 24h change, dominance"],
    ["Global", "US indices, gold, crude oil, DXY"],
    ["News + Events", "India market news; GDP, jobs, Fed, RBI calendar with dates"],
    ["Portfolio", "apne holdings add karo — live P&L (EOD prices se)"],
    ["Learn + Studies + My Notes", "strategies, glossary, aapka notebook (stage rules, SL hunting, dead cat bounce), Sensex 1979-2024 history, budget-day study"]
  ];
  var card = document.createElement("details");
  card.className = "gl"; card.id = "siteGuideCard"; card.style.marginTop = "12px";
  card.innerHTML = '<summary><b>About Market Brain — kya hai, kya data hai, kaise kaam karta hai</b></summary>' +
    '<div class="note" style="margin-bottom:10px">Ye aapka personal market terminal hai — <b>100% free sources</b> se (NSE/BSE bhavcopy, yfinance, TradingView, chartink, RBI/Fed calendars). Data <b>GitHub Actions</b> se roz automatically collect hota hai (koi PC nahi chahiye). Mobile-first hai — phone par hi bana hai. Password-locked private site hai.</div>' +
    '<div class="note" style="margin-bottom:10px"><b>Data refresh timings (IST):</b> stocks/indices/crypto/news ~roz subah-dopahar · futures EOD ~18:50 · events 6:10 AM · AI TimesFM 8:35 PM · fundamentals weekly · sab kuch automatic.</div>' +
    S.map(function (x) { return "<details style=\"margin:6px 0\"><summary><b>" + esc(x[0]) + "</b></summary><div class=\"note\" style=\"margin-top:5px\">" + esc(x[1]) + "</div></details>"; }).join("") +
    '<div class="footer-note">capabilities: 2,300+ stocks · 139 indices · 100 coins · AI forecasts · sab browser mein, data raw JSON se publicly readable</div>';
  var eb = document.getElementById("eduBox");
  if (eb && eb.previousSibling) LN.insertBefore(card, eb);
  else LN.appendChild(card);
})();
