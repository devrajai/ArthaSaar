#!/usr/bin/env python3
"""mf_top.py — popular funds ki 1Y/3Y/5Y returns vs Nifty (free data).
Reads data/mf.json (AMFI), picks a curated list of well-known Direct-Growth
funds, fetches full NAV history from api.mfapi.in (free, no key) and computes
trailing returns. Nifty side comes from data/index-history.json (monthly %).
Output: data/mf-top.json (small, for the site's Top Performers card).
"""
import json, time, datetime as dt, urllib.request

def jget(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "ignore"))

PICKS = [
    "Axis Large Cap Fund", "HDFC Large Cap Fund", "SBI Large Cap Fund", "Mirae Asset Large Cap Fund",
    "ICICI Prudential Large & Mid Cap Fund", "Parag Parikh Flexi Cap Fund", "HDFC Flexi Cap Fund",
    "Axis Midcap Fund", "HDFC Mid Cap Fund", "Quant Mid Cap Fund",
    "SBI SMALL CAP FUND", "Axis Small Cap Fund", "Nippon India Small Cap Fund",
    "Tata Small Cap Fund", "Quant Small Cap Fund",
    "Mirae Asset ELSS Tax Saver Fund", "Quant ELSS Tax Saver Fund",
    "UTI Nifty 50 Index Fund", "HDFC Nifty 50 Index Fund", "Kotak Nifty 50 Index Fund",
    "Axis Nifty 50 Index Fund", "Mirae Asset Nifty 50 Index Fund", "DSP Nifty 50 Index Fund",
    "UTI - Nifty Next 50 Index Fund", "Tata Digital India Fund",
    "SBI TECHNOLOGY OPPORTUNITIES FUND", "Kotak Equity Savings Fund",
    "HDFC Balanced Advantage Fund", "Edelweiss Balanced Advantage Fund",
    "SBI GOLD FUND", "SBI FOCUSED FUND", "UTI Nifty 500 Value 50 Index Fund",
    "DSP Nifty 50 Equal Weight Index Fund", "ICICI Prudential Value Fund",
]

mf = json.load(open("data/mf.json"))
sel = {}
for kw in PICKS:
    for f in mf.get("funds", []):
        n = (f.get("n") or "")
        if kw.lower() in n.lower() and "direct" in n.lower() and "growth" in n.lower() and "idcw" not in n.lower():
            sel[f["c"]] = f
            break

# ---- nifty trailing (monthly % compounding) ----
def nifty_trailing(months):
    try:
        ih = json.load(open("data/index-history.json"))
        row = next(x for x in ih.get("indices", []) if x.get("key") == "nifty")
        pts = []
        for y, ms in row.get("years", {}).items():
            for m, v in ms.items():
                pts.append((int(y), int(m), float(v)))
        pts.sort()
        pts = pts[-months:]
        r = 1.0
        for _, _, v in pts:
            r *= (1 + v / 100.0)
        return round((r - 1) * 100, 1)
    except Exception:
        return None

def parse_d(s):
    p = s.split("-")
    return dt.date(int(p[2]), int(p[1]), int(p[0]))

def trailing(hist, days):
    if not hist:
        return None
    now = float(hist[0]["nav"])
    cutoff = parse_d(hist[0]["date"]) - dt.timedelta(days=days)
    last = None
    for x in reversed(hist):  # oldest -> newest
        if parse_d(x["date"]) <= cutoff:
            last = float(x["nav"])
        else:
            break
    if not last:
        return None
    return round((now / last - 1) * 100, 1)

rows, failed = [], []
for code, f in sel.items():
    try:
        d = jget("https://api.mfapi.in/mf/%s" % code)
        hist = (d or {}).get("data") or []
        if len(hist) < 250:
            failed.append(f["n"]); continue
        rows.append({"c": code, "n": f["n"], "k": f.get("k") or "",
                     "r1": trailing(hist, 365), "r3": trailing(hist, 1095), "r5": trailing(hist, 1825)})
        time.sleep(0.25)
    except Exception as e:
        failed.append(f["n"] + " (" + str(e)[:40] + ")")

rows = [r for r in rows if r["r3"] is not None]
rows.sort(key=lambda r: -(r["r3"] or -999))
out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
       "count": len(rows),
       "nifty": {"r1": nifty_trailing(12), "r3": nifty_trailing(36), "r5": nifty_trailing(60)},
       "funds": rows,
       "failed": failed[:10]}
json.dump(out, open("data/mf-top.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("mf-top.json: %d funds, %d failed" % (len(rows), len(failed)))
for r in rows[:5]:
    print("  ", r["n"][:44], r["r1"], r["r3"], r["r5"])
