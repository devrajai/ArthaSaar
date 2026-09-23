#!/usr/bin/env python3
"""News Volume Tracker - Google News RSS (free) - 7-day article volume + keyword sentiment.
Tracks Nifty heavyweights: spike in coverage = kuch ho raha hai.
Data: data/news-volume.json (merged daily, keeps 28-day history)."""
import json, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import os, sys

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST)
TODAY = NOW.date().isoformat()
KEEP_DAYS = 28

# Nifty 40 watchlist: (symbol, search query)
WATCH = [
    ("RELIANCE", "Reliance Industries"),
    ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"),
    ("ICICIBANK", "ICICI Bank"),
    ("INFY", "Infosys"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("SBIN", "State Bank of India SBI"),
    ("LT", "Larsen & Toubro L&T"),
    ("ITC", "ITC share OR ITC Ltd"),
    ("HINDUNILVR", "Hindustan Unilever"),
    ("BAJFINANCE", "Bajaj Finance"),
    ("MARUTI", "Maruti Suzuki"),
    ("AXISBANK", "Axis Bank"),
    ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("TATAMOTORS", "Tata Motors"),
    ("SUNPHARMA", "Sun Pharmaceutical"),
    ("TITAN", "Titan Company share"),
    ("ASIANPAINT", "Asian Paints"),
    ("BAJAJFINSV", "Bajaj Finserv"),
    ("WIPRO", "Wipro share"),
    ("HCLTECH", "HCL Technologies"),
    ("ADANIENT", "Adani Enterprises"),
    ("ADANIPORTS", "Adani Ports"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("NTPC", "NTPC power"),
    ("POWERGRID", "Power Grid Corporation"),
    ("ONGC", "ONGC oil"),
    ("COALINDIA", "Coal India"),
    ("TATASTEEL", "Tata Steel"),
    ("JSWSTEEL", "JSW Steel"),
    ("HINDALCO", "Hindalco"),
    ("M&M", "Mahindra and Mahindra share"),
    ("TECHM", "Tech Mahindra"),
    ("NESTLEIND", "Nestle India"),
    ("BAJAJ-AUTO", "Bajaj Auto"),
    ("HEROMOTOCO", "Hero MotoCorp"),
    ("EICHERMOT", "Eicher Motors Royal Enfield"),
    ("GRASIM", "Grasim Industries"),
    ("CIPLA", "Cipla"),
    ("DRREDDY", "Dr Reddy's Laboratories"),
    ("DIVISLAB", "Divi's Laboratories"),
]

POS = ["surge","soar","soars","jump","jumps","rally","rallies","profit","profits","beat","beats","record high","upgrade","upgrades","buy","outperform","gain","gains","rise","rises","rose","boost","award","order win","wins order","expansion","dividend","bonus","growth","strong","bullish","partnership","mou","approval","approves","subsscribed","subscribe","multi-year high","all-time high","52-week high","invest","stake","raises","higher","top"]
NEG = ["fall","falls","fell","plunge","plunges","plummet","plummets","drop","drops","slump","slumps","loss","losses","decline","declines","slip","slips","down","crash","probe","fraud","scam","raid","arrest","resign","resigns","penalty","fine","fines","downgrade","sell","underperform","weak","cut","cuts","default","fire","strike","lawsuit","complaint","layoff","layoffs","shut","blocked","ban","warning","tank","tanks","sink","sinks","crash","red","fraud","miss","misses","lower","low","slide","hits 52-week low","plunges","recall","censure","dispute","litigation","grievance"]

def sentiment(titles):
    p = n = 0
    tl = [x.lower() for x in titles]
    for t in tl:
        for w in POS:
            if w in t: p += 1; break
        for w in NEG:
            if w in t: n += 1; break
    tot = p + n
    if tot == 0: return 0, "neutral"
    s = round(100 * (p - n) / tot)
    tag = "positive" if s >= 25 else ("negative" if s <= -25 else "neutral")
    return s, tag

def fetch_rss(q, retries=2):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:7d") + "&hl=en-IN&gl=IN&ceid=IN:en"
    for a in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return ET.fromstring(r.read())
        except Exception as e:
            if a >= retries: return None
            time.sleep(3)
    return None

def load_old(path):
    if os.path.exists(path):
        try:
            d = json.load(open(path))
            if isinstance(d.get("hist"), dict): return d
        except Exception: pass
    return {"hist": {}}

def main():
    out_path = "data/news-volume.json"
    old = load_old(out_path)
    hist = old["hist"]  # {symbol: {date: count}}
    cutoff = (NOW - timedelta(days=KEEP_DAYS)).date().isoformat()

    companies = []
    for sym, q in WATCH:
        root = fetch_rss(q)
        items = []
        if root is not None:
            for it in root.iter("item"):
                try:
                    title = (it.findtext("title") or "").strip()
                    pd = it.findtext("pubDate") or ""
                    src = (it.findtext("source") or "").strip()
                    if not title or not pd: continue
                    dt = parsedate_to_datetime(pd).astimezone(IST)
                    items.append((title, dt, src))
                except Exception: continue
        # per-day counts (merge with history)
        days = hist.get(sym, {})
        days = {k: v for k, v in days.items() if k >= cutoff}
        for _, dt, _ in items:
            k = dt.date().isoformat()
            days[k] = days.get(k, 0) + 1
        hist[sym] = days

        # last 7 days series (oldest -> newest)
        series = []
        for i in range(6, -1, -1):
            d = (NOW - timedelta(days=i)).date().isoformat()
            series.append(days.get(d, 0))
        total7 = sum(series)
        prior = series[:6]; prior_avg = (sum(prior) / 6.0) if len(prior) == 6 else (total7 / 7.0)
        today = series[-1]
        spike = round(today / prior_avg, 2) if prior_avg >= 0.5 else (2.5 if today >= 3 else 1.0)

        # recent headlines: top 5 by recency (dedup by title prefix)
        seen, hl = set(), []
        for t, dt, s in sorted(items, key=lambda x: x[1], reverse=True):
            k = t[:60].lower()
            if k in seen: continue
            seen.add(k)
            if " - " in t: t, ds = t.rsplit(" - ", 1)[0], t.rsplit(" - ", 1)[1]
            else: ds = s
            hl.append({"t": t[:140], "s": ds[:40], "d": dt.strftime("%d %b")})
            if len(hl) >= 5: break
        sc, tag = sentiment([h["t"] for h in hl])
        companies.append({
            "sym": sym, "q": q, "d7": series, "total7": total7,
            "spike": spike, "sent": sc, "tag": tag, "hl": hl
        })
        time.sleep(1.2)

    companies.sort(key=lambda c: (-(c["spike"] if c["total7"] > 0 else 0), -c["total7"]))
    out = {
        "updated": NOW.strftime("%d %b %Y, %H:%M IST"),
        "note": "Google News RSS - article count last 7 days. Spike = aaj vs pichle 6 din ka avg. Sentiment = headline keywords (rule-based, indicative only - not advice).",
        "count": len(companies),
        "companies": companies,
        "hist": {k: {d: c for d, c in v.items() if d >= cutoff} for k, v in hist.items()}
    }
    os.makedirs("data", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote", out_path, "-", len(companies), "companies")
    top = [c for c in companies if c["total7"] > 0][:5]
    for c in top:
        print(f"  {c['sym']:12s} 7d={c['total7']:3d} spike={c['spike']} sent={c['sent']} {c['tag']}")

if __name__ == "__main__":
    main()
