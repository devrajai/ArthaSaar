#!/usr/bin/env python3
"""economy_pulse.py - Economy Pulse card data: 11 indicators (GST, Rail, Ports,
Auto, EPFO, Power, GDP, CPI, PMI, Core, FII). Values/yoy MANUALLY VERIFIED
(regex removed - it produced garbage); only headlines auto-fetch from Google
News RSS daily. FII monthly bars in 'm' field (NSDL data, manual update)."""
import json, os, re, time, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST)

# query + required keywords per indicator
QUERIES = {
    "gst": ("India GST collection crore monthly", ["gst"]),
    "rail": ("Indian Railways freight loading million tonnes", ["railway", "freight", "loading"]),
    "port": ("India ports container cargo traffic JNPT Mundra", ["port", "container", "cargo", "traffic"]),
    "auto": ("India monthly car sales Maruti Tata Mahindra", ["sales", "units", "maruti", "tata", "mahindra", "hyundai"]),
    "epfo": ("EPFO payroll data net member addition", ["epfo", "provident"]),
    "power": ("India power demand peak electricity", ["power", "electricity", "gigawatt", " demand"]),
    "gdp": ("India GDP growth quarterly MoSPI", ["gdp"]),
    "cpi": ("India retail inflation CPI MoSPI", ["inflation", "cpi"]),
    "pmi": ("India PMI manufacturing services HSBC", ["pmi", "purchasing"]),
    "core": ("India core sector growth index industries", ["core", "infrastructure output", "ici", "industrial"]),
    "fii": ("FPI FII buying selling Indian equities crore month", ["fii", "fpi", "foreign"]),
}

def fetch_headlines(q, must, days=30, n=4):
    base = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:" + str(days) + "d") + "&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        req = urllib.request.Request(base, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    except Exception:
        return []
    out = []
    for m in re.finditer(r"<item>(.*?)</item>", xml, re.S):
        item = m.group(1)
        t = re.search(r"<title>(.*?)</title>", item, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        if not t:
            continue
        title = re.sub(r"\s+", " ", t.group(1)).strip()
        src, _, title = title.rpartition(" - ")
        low = title.lower()
        if must and not any(k in low for k in must):
            continue
        try:
            dt = datetime.strptime(d.group(1), "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - dt) > timedelta(days=days + 1):
                continue
            ds = dt.astimezone(IST).strftime("%d %b")
        except Exception:
            ds = ""
        out.append({"t": title[:140], "s": (src or "news")[:32], "d": ds})
        if len(out) >= n:
            break
    return out

def main():
    path = "data/economy-pulse.json"
    d = {}
    if os.path.exists(path):
        try:
            d = json.load(open(path))
        except Exception:
            d = {}
    byid = {}
    for it in d.get("ind", []):
        if isinstance(it, dict) and it.get("id"):
            byid[it["id"]] = it
    for iid, (q, must) in QUERIES.items():
        it = byid.get(iid)
        if not it:
            continue
        it["hl"] = fetch_headlines(q, must)
        byid[iid] = it
        time.sleep(1.0)

    order = ["gst", "rail", "port", "auto", "epfo", "power", "gdp", "cpi", "pmi", "core", "fii"]
    ind = [byid.get(k, {}) for k in order]
    out = {
        "updated": NOW.strftime("%d %b %Y, %H:%M IST"),
        "note": "Govt monthly/weekly releases. Main figures sources se verified; headlines roz auto-update (Google News). Indicative only - not advice.",
        "ind": ind,
    }
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote", path, "-", len(ind), "indicators")

if __name__ == "__main__":
    main()
