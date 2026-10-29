#!/usr/bin/env python3
"""Monthly price history per stock, back to 2019, for drawing a real chart.

WHY A SEPARATE FILE
docs/series.json already holds 120 daily closes per stock - enough for a sparkline, not
enough to see a shape. The full archive is 1,928 sessions x 3,510 symbols, which is 3.5M
points and cannot be published.

So this takes the LAST CLOSE OF EACH MONTH instead. 92 months from 2019 to today is enough
to see a multi-year trend, and at ~2,200 stocks it lands around 1.5 MB - which is only
fetched when someone opens a stock, never on first paint.

MONTHLY IS A REAL TRADEOFF, stated plainly on the page: it shows the trend and the drawdowns
but hides the daily noise, so a 3-day crash reads as one bad month. That is fine for
"what has this done since 2019" and wrong for "what did it do last week" - which is what the
daily series and the live intraday candles are for.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/charts.json"
ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
MAX_STOCKS = 2500


def main():
    import duckdb

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "series": {}, "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive, so no price history is published."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("charts: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1300MB'")
    con.execute("SET preserve_insertion_order=false")

    # last close of each (symbol, month). DuckDB does the grouping, so we never hold the
    # full 3.5M rows in pandas.
    rows = con.execute("""
      -- substr on the ISO date string, not strftime: this DuckDB build only accepts
      -- TIMESTAMP for strftime, and `date` is a DATE column.
      WITH m AS (
        SELECT symbol,
               substr(CAST(date AS VARCHAR), 1, 7) AS ym,
               close,
               row_number() OVER (PARTITION BY symbol, substr(CAST(date AS VARCHAR), 1, 7)
                                  ORDER BY date DESC) AS rn
        FROM read_parquet(?)
        WHERE close > 0
      )
      SELECT symbol, ym, close FROM m WHERE rn = 1 ORDER BY symbol, ym
    """, [arch]).fetchall()
    con.close()

    if not rows:
        out["note"] = "The archive produced no monthly closes."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("charts: skipped (empty)")
        return 0

    series = {}
    for sym, ym, close in rows:
        series.setdefault(sym, {})[ym] = round(float(close), 2)

    # keep the symbols with the most months, so the file stays bounded
    if len(series) > MAX_STOCKS:
        keep = sorted(series, key=lambda s: -len(series[s]))[:MAX_STOCKS]
        series = {k: series[k] for k in keep}

    # flatten to {sym: [[ym, close], ...]} - shorter than objects and keeps the order
    flat = {}
    for sym, d in series.items():
        flat[sym] = [[ym, d[ym]] for ym in sorted(d)]

    out["series"] = flat
    out["count"] = len(flat)
    months = sorted({ym for v in flat.values() for ym, _ in v})
    out["months"] = len(months)
    out["from"], out["to"] = (months[0], months[-1]) if months else (None, None)
    out["note"] = ("Month-end closes since 2019, for drawing a multi-year shape. Monthly bars "
                   "hide daily noise - use the daily series or the live candles for short-term "
                   "moves.")
    out["cautions"] = {
        "monthly": ("One point per month. A crash that recovered inside a month is invisible "
                    "here."),
        "adjusted": "Split and bonus adjusted, so a 1:10 split does not read as a 90% fall.",
        "survivorship": "Only stocks listed today are included.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f MB  |  %d symbols, %d months (%s to %s)"
          % (OUT, os.path.getsize(OUT) / 1e6, out["count"], out["months"],
             out["from"], out["to"]))

    for sym in ("RELIANCE", "TCS", "HDFCBANK"):
        if sym in flat:
            pts = flat[sym]
            print("   %-10s %d months, first %s = %.2f, last %s = %.2f"
                  % (sym, len(pts), pts[0][0], pts[0][1], pts[-1][0], pts[-1][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
