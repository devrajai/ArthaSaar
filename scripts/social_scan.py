#!/usr/bin/env python3
"""social_scan.py - Reddit (free JSON API) se Indian stock mentions + sentiment.
Writes data/social.json (trending stocks + buzz). Kabhi block ho to khali data likhta hai, fail nahi hota."""
import sys, json, re, time, urllib.request, datetime
sys.path.insert(0, "scripts")
from tghelp import jload, IST

SUBS = ["IndianStockMarket", "IndiaInvestments", "StockMarketIndia"]
POS = set("surge rally jump beat record gain upgrade bullish boom strong growth rise boost recovery breakout multibagger".split())
NEG = set("crash plunge fall slump drop decline weak loss downgrade bearish fear warning fraud scam miss slid downside".split())

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36", "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"))

SYMS = set()
sc = jload("data/brain-screener.json")
for s in (sc.get("stocks") or []):
    if s.get("symbol"): SYMS.add(s["symbol"])

counts = {}
def bump(name, sentiment):
    e = counts.setdefault(name, {"n": 0, "pos": 0})
    e["n"] += 1
    if sentiment > 0: e["pos"] += 1

total_posts = 0
SOURCES_OK = 0
for sub in SUBS:
    try:
        d = get("https://www.reddit.com/r/%s/hot.json?limit=50" % sub)
        for ch in (d.get("data") or {}).get("children") or []:
            p = (ch.get("data") or {})
            title = (p.get("title") or "") + " " + (p.get("selftext") or "")[:400]
            low = title.lower()
            words = set(re.findall(r"[a-z]+", low))
            sent = len(words & POS) - len(words & NEG)
            for sym in SYMS:
                if sym.lower() in low or (" " + sym.lower() + " ") in (" " + low + " "):
                    bump(sym, sent)
            total_posts += 1
    except Exception as e:
        print("sub fail", sub, str(e)[:50])
    else:
        SOURCES_OK += 1
    time.sleep(1.2)

trend = sorted(({"sym": k, "n": v["n"], "pos_pct": round(100 * v["pos"] / v["n"])} for k, v in counts.items() if v["n"] >= 2),
               key=lambda x: (-x["n"], -x["pos_pct"]))[:15]
out = {"updated": datetime.datetime.now(IST).isoformat(),
       "source": "Reddit r/IndianStockMarket + r/IndiaInvestments + r/StockMarketIndia (free JSON)",
       "posts_scanned": total_posts, "sources_ok": SOURCES_OK, "trending": trend}
json.dump(out, open("data/social.json", "w"), indent=1)
print("social:", total_posts, "posts | sources ok:", SOURCES_OK, "| trending:", [t["sym"] for t in trend[:5]])
