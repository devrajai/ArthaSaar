#!/usr/bin/env python3
"""A daily history you can search by date, month or year.

WHY THIS EXISTS
The site had ten years of daily facts scattered across separate files - Nifty closes in one,
India VIX in another, PCR and max pain in a third - and no way to ask "what happened on
14 March 2023?". You could see today, or a chart, but not a specific day.

This joins them into one row per session and publishes it, so the page can answer a date
query directly instead of making the reader cross-reference four tables.

WHAT IS IN EACH ROW
  date        the session
  close       Nifty close
  chg_pct     move against the previous session
  big         whether it was a big day (|move| >= 1.5%, the same definition used everywhere)
  vix         India VIX close, when known
  pcr         Nifty put-call ratio from the F&O open interest, when known
  max_pain    Nifty max-pain strike, when known

SOURCES, AND WHY THEY START AT DIFFERENT DATES
  Nifty      Yahoo Finance, 10 years
  India VIX  Yahoo Finance, 10 years
  PCR        our own F&O archive, from 2019 only - before that we never collected it
A missing value is left empty rather than filled in. The page shows a dash.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = "docs/history.json"
NIFTY = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=10y"
BIG = 1.5


def read_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


def nifty():
    import datetime as dt
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(NIFTY, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        rows = [(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"), c)
                for t, c in zip(r["timestamp"], q["close"]) if c is not None]
        rows.sort()
        return rows
    except Exception as e:
        print("  nifty fetch failed: %s" % type(e).__name__)
        return []


def main():
    bars = nifty()
    if len(bars) < 200:
        print("history: not enough Nifty data")
        return 0

    vix = {}
    v = read_json("docs/vix.json")
    if v:
        for pair in (v.get("series") or []):
            try:
                vix[str(pair[0])[:10]] = round(float(pair[1]), 2)
            except Exception:
                continue

    pcr, pain = {}, {}
    o = read_json("docs/oi_history.json")
    if o:
        for row in (o.get("series") or []):
            if row.get("i") != "N":
                continue
            d = str(row.get("d"))[:10]
            if row.get("p") is not None:
                pcr[d] = round(float(row["p"]), 3)
            if row.get("x") is not None:
                pain[d] = row["x"]

    out_rows = []
    prev = None
    for d, c in bars:
        chg = round((c / prev - 1) * 100, 2) if prev else None
        out_rows.append({
            "d": d,
            "c": round(float(c), 2),
            "chg": chg,
            "big": (chg is not None and abs(chg) >= BIG),
            "vix": vix.get(d),
            "pcr": pcr.get(d),
            "mp": pain.get(d),
        })
        prev = c

    # year and month roll-ups, so a reader can start from a period and drill in
    years, months = {}, {}
    for r in out_rows:
        if r["chg"] is None:
            continue
        y, m = r["d"][:4], r["d"][:7]
        for key, bucket in ((y, years), (m, months)):
            b = bucket.setdefault(key, {"n": 0, "up": 0, "big": 0, "sum": 0.0,
                                        "worst": 0.0, "best": 0.0})
            b["n"] += 1
            b["sum"] += r["chg"]
            if r["chg"] > 0:
                b["up"] += 1
            if r["big"]:
                b["big"] += 1
            b["worst"] = min(b["worst"], r["chg"])
            b["best"] = max(b["best"], r["chg"])
    for bucket in (years, months):
        for k, b in bucket.items():
            b["avg"] = round(b.pop("sum") / b["n"], 2) if b["n"] else None
            b["up_pct"] = round(b["up"] / b["n"] * 100) if b["n"] else None
            b.pop("up", None)

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": len(out_rows),
           "first": out_rows[0]["d"], "last": out_rows[-1]["d"],
           "big_threshold_pct": BIG,
           "years": dict(sorted(years.items())),
           "months": dict(sorted(months.items())),
           "rows": out_rows,
           "note": ("One row per session, joined from Nifty closes, India VIX and our own F&O "
                    "archive. Values that were never collected are left empty, not filled in."),
           "cautions": {
               "pcr_from": "PCR starts in 2019 - it was not collected before that.",
               "vix_from": "VIX starts in 2016.",
               "big": "A big day is |move| >= 1.5%, the same definition used across the site.",
           }}

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d sessions, %s -> %s" % (len(out_rows), out["first"], out["last"]))
    print("   %d years, %d months indexed" % (len(years), len(months)))
    withvix = sum(1 for r in out_rows if r["vix"] is not None)
    withpcr = sum(1 for r in out_rows if r["pcr"] is not None)
    print("   rows with VIX: %d | with PCR: %d" % (withvix, withpcr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
