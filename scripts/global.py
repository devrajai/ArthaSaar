#!/usr/bin/env python3
"""global.py - GLOBAL RADAR (ArthaSaar Phase 1):
- Duniya ke indices + commodities ka EOD data (Yahoo Finance free API, 1 saal)
- GLOBAL->INDIA CORRELATION ENGINE: har global market ka NIFTY/sector pe asar
  (same-day + NEXT-DAY lag correlation + shock stats)
Output: data/world.json (data/global.json parallel session ka hai - mat chhedo)
Note: EOD data hai (market close ke baad). Live feed nahi - honest indicative analysis."""
import json, math, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

IST = datetime.now(timezone(timedelta(hours=5, minutes=30)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

GLOBAL = [
    ("^GSPC", "S&P 500", "US", "idx"), ("^IXIC", "Nasdaq", "US", "idx"),
    ("^N225", "Nikkei", "Japan", "idx"), ("^HSI", "Hang Seng", "HongKong", "idx"),
    ("^GDAXI", "DAX", "Germany", "idx"), ("^FTSE", "FTSE 100", "UK", "idx"),
    ("000001.SS", "Shanghai", "China", "idx"), ("^VIX", "VIX (Fear)", "US", "idx"),
    ("GC=F", "Gold", "commodity", "cmd"), ("CL=F", "Crude Oil", "commodity", "cmd"),
    ("HG=F", "Copper", "commodity", "cmd"), ("SI=F", "Silver", "commodity", "cmd"),
    ("INR=X", "USD/INR", "fx", "cmd"),
]
INDIA = [("^NSEI", "NIFTY 50"), ("^NSEBANK", "Bank Nifty"), ("^CNXIT", "Nifty IT"), ("^CNXPHARMA", "Nifty Pharma")]

def fetch(sym, rng="1y"):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (urllib.parse.quote(sym), rng)
    d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    r = d["chart"]["result"]
    if not r:
        return None
    ts = r[0]["timestamp"]
    cl = r[0]["indicators"]["quote"][0]["close"]
    return [(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), c) for t, c in zip(ts, cl) if c]

def stats(rows):
    cl = [c for _, c in rows]
    if len(cl) < 5:
        return None
    last = cl[-1]
    def back(n):
        return (cl[-1 - min(n, len(cl) - 1)] / last - 1.0) * 100 if len(cl) > 1 else 0.0
    hi = max(cl)
    return {"c": round(last, 1), "d1": round(back(1), 2), "d5": round(back(5), 2),
            "m1": round(back(21), 2), "m3": round(back(63), 2), "h52": round((last / hi - 1) * 100, 1),
            "sp": [round(c, 1) for c in cl[-30:]]}

def corr(xs, ys):
    n = min(len(xs), len(ys))
    if n < 20:
        return None
    xs, ys = xs[-n:], ys[-n:]
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 2)

def main():
    series = {}
    out = {"idx": [], "cmd": []}
    for sym, name, grp, kind in GLOBAL:
        try:
            rows = fetch(sym)
            st = stats(rows) if rows else None
            if st:
                st["n"] = name
                out[kind].append(st)
                series[sym] = rows
        except Exception:
            pass
    ind = {}
    for sym, name in INDIA:
        try:
            rows = fetch(sym)
            if rows:
                ind[name] = rows
        except Exception:
            pass
    def chgmap(rows):
        m = {}
        for i in range(1, len(rows)):
            d, c = rows[i]
            pd_, pc = rows[i - 1]
            m[d] = (c / pc - 1) * 100
        return m
    gm = {s: chgmap(r) for s, r in series.items()}
    im = {n: chgmap(r) for n, r in ind.items()}
    nifty_dates = sorted(im.get("NIFTY 50", {}).keys())
    nxt = {}
    for i in range(len(nifty_dates) - 1):
        nxt[nifty_dates[i]] = nifty_dates[i + 1]
    def last90(m):
        return sorted(m.keys())[-90:]
    cors = []
    shock = {}
    for sym, name, grp, kind in GLOBAL:
        if sym not in gm:
            continue
        gk = last90(gm[sym])
        for iname in ind:
            same, lagpairs = [], []
            for d in gk:
                if d in im[iname]:
                    same.append((gm[sym][d], im[iname][d]))
                nd = nxt.get(d)
                if nd and nd in im[iname]:
                    lagpairs.append((gm[sym][d], im[iname][nd]))
            if len(same) >= 20:
                cs = corr([a for a, _ in same], [b for _, b in same])
                cl_ = corr([a for a, _ in lagpairs], [b for _, b in lagpairs]) if len(lagpairs) >= 20 else None
                cors.append({"g": name, "i": iname, "s": cs, "l": cl_})
        if "NIFTY 50" in im:
            ev = []
            for d in gk:
                nd = nxt.get(d)
                if nd and gm[sym][d] < -1.0 and nd in im["NIFTY 50"]:
                    ev.append(im["NIFTY 50"][nd])
            if len(ev) >= 3:
                shock[name] = {"n": len(ev), "avg": round(sum(ev) / len(ev), 2), "up": sum(1 for e in ev if e > 0)}
    out["corr"] = sorted([c for c in cors if c["l"] is not None], key=lambda x: -abs(x["l"] or 0))
    out["shock"] = shock
    out["updated"] = IST.strftime("%d %b %Y, %H:%M IST")
    with open("data/world.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("OK world: idx=%d cmd=%d corr=%d shock=%d | %s" % (len(out["idx"]), len(out["cmd"]), len(out["corr"]), len(shock), out["updated"]))

if __name__ == "__main__":
    main()
