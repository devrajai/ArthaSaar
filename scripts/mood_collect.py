#!/usr/bin/env python3
"""mood_collect.py - AI news sentiment (lexicon-based, no paid API).
Reads data/news.json headlines, scores each headline positive/negative,
builds overall market mood 0-100 + per-stock sentiment. Writes data/mood.json."""
import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

POS = set("""surge surges surged rally rallies rallied jump jumps jumped soar soars soared
beat beats record records record-high high profit profits gain gains gained upgrade upgrades
outperform buy buying bullish boom booming strong stronger growth grows rise rises rose rising
boost boosted win wins winning recovery recover rebounds rebound positive tops hits milestone
expansion expand expands higher upturn breakout multibagger
""".split())

NEG = set("""plunge plunges plunged crash crashes crashed fall falls fell falling slump slumps
drop drops dropped decline declines declined weak weaker loss losses downgrade downgrades
sell selling selling-pressure bearish bear fear fears warning warns probe probes fraud scam
default defaults miss misses missed below disappointing disappoints slid slides slid
downside layoffs cut cuts slashed fined penalty raid raided
""".split())

INTENSIFIERS = {"big", "sharp", "steep", "massive", "hefty", "heavily", "major", "huge", "sharply"}
STOCKS = {
    "reliance": "RELIANCE", "tcs": "TCS", "hdfc bank": "HDFCBANK", "icici": "ICICIBANK",
    "infosys": "INFY", "sbi": "SBIN", "infy": "INFY", "tata steel": "TATASTEEL",
    "tata motors": "TATAMOTORS", "bajaj finance": "BAJFINANCE", "adani": "ADANI",
    "airtel": "BHARTIARTL", "larsen": "LT", "itc": "ITC", "sun pharma": "SUNPHARMA",
    "axis bank": "AXISBANK", "kotak": "KOTAKBANK", "lupin": "LUPIN", "cipla": "CIPLA",
    "dr reddy": "DRREDDY", "coal india": "COALINDIA", "ongc": "ONGC", "ntpc": "NTPC",
    "power grid": "POWERGRID", "asian paints": "ASIANPAINT", "maruti": "MARUTI",
    "mahindra": "M&M", "eicher": "EICHERMOT", "bajaj auto": "BAJAJ-AUTO", "hero": "HEROMOTOCO",
    "wipro": "WIPRO", "hcl": "HCLTECH", "tech mahindra": "TECHM", "zomato": "ETERNAL",
    "eternal": "ETERNAL", "swiggy": "SWIGGY", "paytm": "PAYTM", "yes bank": "YESBANK",
    "punjab national": "PNB", "bank of baroda": "BANKBARODA", "canara": "CANBK",
    "hal": "HAL", "bpcl": "BPCL", "ioc": "IOC", "gail": "GAIL", "sail": "SAIL",
    "jsw": "JSWSTEEL", "vedanta": "VEDL", "hindalco": "HINDALCO",
    "ultratech": "ULTRACEMCO", "dabur": "DABUR", "nestle": "NESTLEIND", "titan": "TITAN",
    "trent": "TRENT", "dmart": "DMART", "idea": "IDEA",
}


def load_news():
    try:
        return json.load(open(DATA / "news.json")).get("items") or []
    except Exception:
        return []


def score_headline(t):
    words = re.findall(r"[a-z]+", t.lower())
    if not words:
        return 0, 0, 0
    p = sum(1 for w in words if w in POS)
    n = sum(1 for w in words if w in NEG)
    boost = 1.5 if any(w in INTENSIFIERS for w in words) else 1.0
    return p, n, boost


def classify(p, n):
    d = (p - n)
    if d >= 2: return 78
    if d == 1: return 64
    if d == 0: return 50
    if d == -1: return 36
    return 22


def main():
    items = load_news()
    scored = []
    stock_hits = {}
    for it in items:
        t = (it.get("title") or "").split(" By ")[0].split(" - ")[0]
        p, n, boost = score_headline(t)
        sc = classify(p, n)
        if p > n:
            sc = min(95, sc * boost)
        elif n > p:
            sc = max(5, sc / boost)
        low = t.lower()
        for name, sym in STOCKS.items():
            if name in low:
                e = stock_hits.setdefault(sym, {"s": 0.0, "n": 0})
                e["s"] += sc
                e["n"] += 1
        scored.append({"t": t, "s": round(sc), "pub": it.get("publisher") or "",
                       "topic": it.get("topic") or "", "link": it.get("link") or ""})

    overall = round(sum(x["s"] for x in scored) / len(scored)) if scored else 50
    if overall >= 70: tag = "Very Bullish"
    elif overall >= 58: tag = "Bullish"
    elif overall >= 42: tag = "Neutral"
    elif overall >= 30: tag = "Bearish"
    else: tag = "Very Bearish"

    pos = sorted(scored, key=lambda x: -x["s"])[:4]
    neg = sorted(scored, key=lambda x: x["s"])[:4]
    stocks = sorted(({"sym": k, "s": round(v["s"] / v["n"]), "n": v["n"]}
                     for k, v in stock_hits.items() if v["n"] >= 2),
                    key=lambda x: -x["s"])[:10]

    out = {
        "updated": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
        "method": "lexicon word-score on news headlines (free, rule-based AI)",
        "overall": overall, "tag": tag, "counted": len(scored),
        "pos": pos, "neg": neg, "stocks": stocks,
        "note": "0-100 scale: >58 bullish, 42-58 neutral, <42 bearish. Approximation hai, tip nahi.",
    }
    json.dump(out, open(DATA / "mood.json", "w"), indent=1)
    print("mood:", overall, tag, "| headlines:", len(scored), "| stocks:", len(stocks))


if __name__ == "__main__":
    main()
