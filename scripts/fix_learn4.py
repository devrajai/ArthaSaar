#!/usr/bin/env python3
"""fix_learn4.py - (1) guide card: remove TELEGRAM/MOBILE APP/LATEST UPDATES blocks
(2) financelearn.js: expand 10 -> 22 concepts (samriddhisdiary series topics, own words).
Idempotent."""
import re

NEW_CONCEPTS = '''    ["10. Books (beginner se pro)", "Psychology of Money (mindset), Let's Talk Money (Indians ke liye practical), Rich Dad Poor Dad (assets vs liabilities), The Intelligent Investor (value investing bible), Coffee Can Investing (India)."],
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
'''

OLD_LAST = '''    ["10. Books (beginner se pro)", "Psychology of Money (mindset), Let's Talk Money (Indians ke liye practical), Rich Dad Poor Dad (assets vs liabilities), The Intelligent Investor (value investing bible), Coffee Can Investing (India)."]
'''


def main():
    s = open("financelearn.js", encoding="utf-8").read()
    if '"22. Retirement' not in s:
        if OLD_LAST in s:
            s = s.replace(OLD_LAST, NEW_CONCEPTS)
            s = s.replace("Naye members ke liye - trading se pehle ye 10 concepts aane chahiye. Seedha Hinglish, zero jargon.",
                          "Naye members ke liye - trading se pehle ye 22 concepts aane chahiye. Seedha Hinglish, zero jargon. (samriddhisdiary series se inspire, apne words me)")
            s = s.replace("Finance Basics - 10 Concepts (series)", "Finance Basics - 22 Concepts (series)")
            open("financelearn.js", "w", encoding="utf-8").write(s)
            print("financelearn.js: expanded to 22 concepts")
        else:
            print("WARN: financelearn anchor not found")
    else:
        print("financelearn.js: already 22")

    g = open("mbguide.js", encoding="utf-8").read()
    if "LATEST UPDATES" in g:
        for name in ("TELEGRAM", "MOBILE APP", "LATEST UPDATES"):
            g = re.sub(r'\n    h \+= block\("' + name + r'.*?;\n', '\n', g, flags=re.S)
        open("mbguide.js", "w", encoding="utf-8").write(g)
        print("mbguide.js: 3 blocks removed")
    elif "MOBILE APP" not in g and "TELEGRAM" not in g:
        print("mbguide.js: already clean")
    else:
        print("WARN: partial guide state")

    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a9" in idx:
        idx = idx.replace("21sep26a9", "21sep26a10")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to a10")
    elif "21sep26a10" in idx:
        print("index.html: already a10")
    else:
        print("WARN: version anchor not found")


if __name__ == "__main__":
    main()
