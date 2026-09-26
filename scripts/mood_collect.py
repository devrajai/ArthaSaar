#!/usr/bin/env python3
"""mood_collect.py - AI news sentiment (lexicon-based, no paid API).
Reads data/news.json headlines, scores each headline positive/negative,
builds overall market mood 0-100 + per-stock sentiment. Writes data/mood.json.
Headlines ke saath stock names (syms) bhi - title se, aur zaroorat ho to
article body se (Google News link decode karke). """
import json, re, time, html as H
from pathlib import Path
from datetime import datetime, timezone, timedelta
import urllib.request

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
    "tata motors": "TATAMOTORS", "bajaj finance": "BAJFINANCE", "adani ports": "ADANIPORTS", "adani energy": "ADANIENSOL",
    "bel": "BEL", "bharat electronics": "BEL",
    "adani green": "ADANIGREEN", "adani power": "ADANIPOWER", "adani enterprises": "ADANIENT",
    "adani": "ADANIENT", "airtel": "BHARTIARTL", "bharti airtel": "BHARTIARTL",
    "larsen": "LT", "itc": "ITC", "sun pharma": "SUNPHARMA",
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
    # ---- midcap / popular additions (article body match ke liye) ----
    "kalpataru": "KPIL", "itc hotels": "ITCHOTELS", "waaree": "WAAREEENER",
    "pidilite": "PIDILITIND", "polycab": "POLYCAB", "havells": "HAVELLS",
    "irfc": "IRFC", "irctc": "IRCTC", "hudco": "HUDCO", "rvnl": "RVNL",
    "suzlon": "SUZLON", "igl": "IGL", "mgl": "MGL", "indraprastha gas": "IGL",
    "indigo": "INDIGO", "interglobe": "INDIGO", "tata power": "TATAPOWER",
    "tata consumer": "TATACONSUM", "tata chemicals": "TATACHEM", "tata elxsi": "TATAELXSI",
    "voltas": "VOLTAS", "blue star": "BLUESTARCO", "amara raja": "AMARAJABAT",
    "exide": "EXIDEIND", "bharat forge": "BHARATFORG", "ashok leyland": "ASHOKLEY",
    "tvs": "TVSMOTOR", "escorts": "ESCORTS", "cummins": "CUMMINSIND",
    "deepak nitrite": "DEEPAKNTR", "navin fluorine": "NAVINFLUOR", "pi industries": "PIIND",
    "upl": "UPL", "rallis": "RALLIS", "coromandel": "COROMANDEL",
    "astral": "ASTRAL", "supreme industries": "SUPREMEIND", "berger paints": "BERGEPAINT",
    "laxmi organics": "LXCHEM", "clean science": "CLEAN", "vinati organics": "VINATIORGA",
    "divi": "DIVISLAB", "alkem": "ALKEM", "mankind": "MANKIND",
    "max healthcare": "MAXHEALTH", "fortis": "FORTIS", "apollo hospitals": "APOLLOHOSP",
    "apollo": "APOLLOHOSP", "narayana": "NH", "lal pathlab": "LALPATHLAB",
    "metropolis": "METROPOLIS", "ipca": "IPCALAB", "abbott india": "ABBOTINDIA",
    "jb chemicals": "JBCHEPHARM", "indusind": "INDUSINDBK", "rbl bank": "RBLBANK",
    "federal bank": "FEDERALBNK", "bandhan": "BANDHANBNK", "idfc first": "IDFCFIRSTB",
    "cholamandalam": "CHOLAFIN", "l&t finance": "LTF", "muthoot": "MUTHOOTFIN",
    "manappuram": "MANAPPURAM", "pnb housing": "PNBHOUSING", "lic hfl": "LICHSGFIN",
    "bajaj finserv": "BAJAJFINSV", "bajaj holdings": "BAJAJHLDNG",
    "shriram finance": "SHRIRAMFIN", "shriram city": "SHRICITY",
    "ambuja": "AMBUJACEM", "acc": "ACC", "dalmia": "DALBHARAT", "ramco": "RAMCOCEM",
    "shree cement": "SHREECEM", "jklakshmi": "JKLAKSHMI",
    "apollo tyre": "APOLLOTYRE", "mrf": "MRF", "ceat": "CEAT", "jk tyre": "JKTYRE",
    "balkrishna": "BALKRISIND", "srf": "SRF", "aarti industries": "AARTIIND",
    "pix transmission": "PIXTRANS", "sona comstar": "SONACOMS", "jbm": "JBMA",
    "lumax": "LUMAXTECH", "motherson": "SAMMAAN",
    "ideaforge": "IDEAFORGE",
    "happiest minds": "HAPPSTMNDS", "persistent": "PERSISTENT", "coforge": "COFORGE",
    "ltimindtree": "LTIM", "ltim": "LTIM", "mphasis": "MPHASIS", "cyient": "CYIENT",
    "kpit": "KPITTECH", "titan company": "TITAN",
    "kalyan": "KALYANKJIL", "tanishq": "TITAN", "nykaa": "NYKAA",
    "honasa": "HONASA", "emami": "EMAMILTD", "marico": "MARICO", "godrej consumer": "GODREJCP",
    "colgate": "COLPAL", "hul": "HINDUNILVR", "hindustan unilever": "HINDUNILVR",
    "britannia": "BRITANNIA", "vardhman": "VTL",
    "page industries": "PAGEIND", "jubilant": "JUBLFOOD", "devyani": "DEVDYANI",
    "westlife": "WESTLIFE", "sapphire": "SAPPHIRE",
    "irb": "IRB", "gmbrew": "GMBREW", "tube investments": "TIINDIA",
    "bhel": "BHEL", "irb infrastructure": "IRB", "nhpc": "NHPC", "sjvn": "SJVN",
    "prestige": "PRESTIGE", "dlf": "DLF", "oberoi realty": "OBEROIRLTY",
    "godrej properties": "GODREJPROP", "brigade": "BRIGADE", "sobha": "SOBHA",
    "phoenix mills": "PHOENIXLTD", "lodha": "LODHA",
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


def find_stocks(text, limit=6):
    found = []
    for name, sym in STOCKS.items():
        if sym in found:
            continue
        if re.search(r"\b" + re.escape(name) + r"\b", text):
            found.append(sym)
        if len(found) >= limit:
            break
    return found


def article_text(url, max_chars=25000):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        raw = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore")
    except Exception:
        return ""
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return H.unescape(raw).lower()[:max_chars]


GENERIC_HINTS = ("stock", "share", "compan", "midcap", "smallcap", "largecap",
                 "sensex", "nifty", "ipo", "psu", "results", "profit", "q1", "q2", "fpo")


def enrich_with_article(items, top=6):
    """top headlines ke liye: Google News link decode karke article body se stock names."""
    dec = None
    try:
        from googlenewsdecoder import gnewsdecoder
        dec = gnewsdecoder
    except Exception:
        return
    for it in items[:top]:
        if it.get("syms") or not it.get("link"):
            continue
        if not any(w in it["t"].lower() for w in GENERIC_HINTS):
            continue
        try:
            r = dec(it["link"], interval=1, timeout=10)
            tgt = r.get("decoded_url") if r.get("success") else None
        except Exception:
            tgt = None
        if not tgt:
            continue
        body = article_text(tgt)
        if body:
            syms = find_stocks(body, 6)
            if syms:
                it["syms"] = syms
                it["src"] = "article"
        time.sleep(0.5)


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
        syms = find_stocks(low, 4)
        for sym in syms:
            e = stock_hits.setdefault(sym, {"s": 0.0, "n": 0})
            e["s"] += sc
            e["n"] += 1
        scored.append({"t": t, "s": round(sc), "pub": it.get("publisher") or "",
                       "topic": it.get("topic") or "", "link": it.get("link") or "",
                       "syms": syms})

    overall = round(sum(x["s"] for x in scored) / len(scored)) if scored else 50
    if overall >= 70: tag = "Very Bullish"
    elif overall >= 58: tag = "Bullish"
    elif overall >= 42: tag = "Neutral"
    elif overall >= 30: tag = "Bearish"
    else: tag = "Very Bearish"

    pos = sorted(scored, key=lambda x: -x["s"])[:5]
    neg = sorted(scored, key=lambda x: x["s"])[:5]
    # article-body enrichment (top pos/neg jo bina naam ke hain)
    try:
        enrich_with_article(pos)
        enrich_with_article(neg)
    except Exception:
        pass
    pos = pos[:4]
    neg = neg[:4]
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
    print("mood:", overall, tag, "| headlines:", len(scored), "| stocks:", len(stocks),
          "| syms:", sum(1 for x in pos + neg if x.get("syms")))


if __name__ == "__main__":
    main()
