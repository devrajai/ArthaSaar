#!/usr/bin/env python3
"""Year-by-year scoreboard, plus the Diwali countdown.

WHAT THIS IS HONEST ABOUT
The obvious build here is a Samvat-year scoreboard - Nifty from one Diwali to the next. It
needs the Muhurat trading date for every year since 2019. Our market_status.json carries NSE's
holiday list for the CURRENT year only (2026-11-08 is this year's Diwali Laxmi Pujan), so the
historical Muhurat dates are not in our data.

Rather than hardcode dates from memory and publish them as fact, this does the calendar-year
version - fully verifiable from our own archive - and shows the Diwali countdown from NSE's own
file. When the pipeline has captured a few years of holiday lists, the Samvat split becomes
possible without guessing.

WHAT IT SHOWS
For each calendar year: the median stock's return, how many stocks rose, the best and worst
sector, and the single worst day. The median matters more than the index for the same reason
as the case studies - a beginner's portfolio is not 50 large caps.
"""
import json, os, sys
from datetime import datetime, timezone

ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
STATUS = "docs/market_status.json"
STOCKS = "docs/stocks.json"
OUT = "docs/scoreboard.json"


def main():
    import duckdb

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "years": [], "diwali": None, "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("scoreboard: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1400MB'")

    # median close per session, and daily breadth
    rows = con.execute("""
      SELECT CAST(date AS VARCHAR) d, median(close) m, COUNT(*) n
      FROM read_parquet(?) WHERE close > 0 GROUP BY d ORDER BY d
    """, [arch]).fetchall()
    series = [(d, float(m), int(n)) for d, m, n in rows if m]

    breadth = {}
    for r in con.execute("""
      WITH d AS (SELECT CAST(date AS VARCHAR) dd, symbol, close
                 FROM read_parquet(?) WHERE close > 0),
           w AS (SELECT dd, symbol, close,
                        LAG(close) OVER (PARTITION BY symbol ORDER BY dd) prev FROM d)
      SELECT dd, AVG((close - prev) / prev), SUM(CASE WHEN close < prev THEN 1 ELSE 0 END), COUNT(*)
      FROM w WHERE prev IS NOT NULL AND prev > 0 GROUP BY dd
    """, [arch]).fetchall():
        breadth[r[0]] = {"avg_pct": round(float(r[1]) * 100, 2),
                         "fell": int(r[2]), "n": int(r[3])}

    # sector membership, so we can name the best and worst sector each year
    sectors = {}
    try:
        st = json.load(open(STOCKS)).get("stocks") or {}
        for v in st.values():
            if v.get("symbol") and v.get("sector"):
                sectors[v["symbol"]] = v["sector"]
    except Exception:
        pass

    by_year = {}
    for d, m, n in series:
        by_year.setdefault(d[:4], []).append((d, m, n))

    for year in sorted(by_year):
        pts = by_year[year]
        if len(pts) < 20:
            continue
        first, last = pts[0], pts[-1]
        ret = (last[1] / first[1] - 1) * 100
        worst_day = min((breadth.get(d) for d, _, _ in pts if d in breadth),
                        key=lambda x: x["avg_pct"], default=None)
        out["years"].append({
            "year": year,
            "from": first[0], "to": last[0],
            "sessions": len(pts),
            "median_return_pct": round(ret, 1),
            "start_level": round(first[1], 1),
            "end_level": round(last[1], 1),
            "worst_day": worst_day,
        })

    # best and worst sector per year needs per-sector returns; do it in one query
    if sectors:
        try:
            sec_rows = con.execute("""
              WITH d AS (SELECT CAST(date AS VARCHAR) dd, symbol, close
                         FROM read_parquet(?) WHERE close > 0),
                   y AS (SELECT substr(dd,1,4) yr, symbol, dd, close,
                                FIRST_VALUE(close) OVER (PARTITION BY symbol, substr(dd,1,4)
                                                         ORDER BY dd) f,
                                LAST_VALUE(close) OVER (PARTITION BY symbol, substr(dd,1,4)
                                                        ORDER BY dd
                                                        ROWS BETWEEN UNBOUNDED PRECEDING
                                                        AND UNBOUNDED FOLLOWING) l
                         FROM d)
              SELECT yr, symbol, MAX((l - f) / f) * 100 r FROM y GROUP BY yr, symbol
            """, [arch]).fetchall()
            per = {}
            for yr, sym, r in sec_rows:
                sec = sectors.get(sym)
                if not sec or r is None:
                    continue
                per.setdefault(yr, {}).setdefault(sec, []).append(float(r))
            for y in out["years"]:
                secs = per.get(y["year"], {})
                med = {s: sorted(v)[len(v) // 2] for s, v in secs.items() if len(v) >= 3}
                if med:
                    best = max(med, key=med.get)
                    worst = min(med, key=med.get)
                    y["best_sector"] = {"name": best, "pct": round(med[best], 1)}
                    y["worst_sector"] = {"name": worst, "pct": round(med[worst], 1)}
        except Exception as e:
            print("  sector split skipped: %s" % type(e).__name__)

    con.close()

    # Diwali countdown, from NSE's own holiday file
    if os.path.exists(STATUS):
        try:
            st = json.load(open(STATUS))
            for d, label in (st.get("holidays") or []):
                if "diwali" in str(label).lower():
                    days = (datetime.strptime(d, "%Y-%m-%d").date()
                            - datetime.now(timezone.utc).date()).days
                    out["diwali"] = {"date": d, "label": label, "days_away": days}
                    break
        except Exception:
            pass

    out["note"] = ("Calendar-year returns on the median listed stock. A Samvat-year scoreboard "
                   "needs the Muhurat trading date for each year, which our holiday file only "
                   "carries for the current year - so that version is not published rather than "
                   "guessed.")
    out["cautions"] = {
        "median": "Median of every listed stock that year, not the index.",
        "survivorship": "Only stocks listed today are included.",
        "samvat": ("The Samvat year runs Diwali to Diwali. Historical Muhurat dates are not in "
                   "our data, so these are calendar years."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for y in out["years"]:
        bs = y.get("best_sector") or {}
        ws = y.get("worst_sector") or {}
        print("   %s  median %+6.1f%%  (%d sessions)  best %s %s%%  worst %s %s%%"
              % (y["year"], y["median_return_pct"], y["sessions"],
                 bs.get("name", "-"), bs.get("pct", "-"),
                 ws.get("name", "-"), ws.get("pct", "-")))
    if out["diwali"]:
        print("   Diwali: %s in %d days" % (out["diwali"]["date"], out["diwali"]["days_away"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
