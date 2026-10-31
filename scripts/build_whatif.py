#!/usr/bin/env python3
"""What if? Two numbers that change behaviour more than any chart.

1. LOSS PREVIEW - for each stock, its worst peak-to-trough fall, with the actual dates, so
   the site can say "this fell 45% between Jan 2020 and Mar 2020. If that repeats, Rs 50,000
   becomes Rs 27,500." A rupee figure lands harder than a warning label.

2. MISSING THE BEST DAYS - what Rs 1 lakh in the Nifty became since 2019, and what it became
   if you missed the 5, 10, 20 or 30 best days. This is the single most useful lesson for
   someone who panic-sells, and almost no free Indian site shows it on their own data.

WHY THE DRAWDOWN DATES MATTER
report_cards.json already has max_drawdown_pct, but a number without dates is forgettable.
"This fell 45%" is abstract; "this fell 45% between 15 Jan and 23 Mar 2020" is a memory.

HONEST LIMITS
- Drawdowns use the split-adjusted close, so a 1:10 split is not a 90% crash.
- The index figures use the Nifty close. If the index series is unavailable the section is
  omitted rather than computed from something else.
- "Missing the best days" assumes you were invested the whole time and simply missed those
  days. It is an illustration of volatility, not a strategy.
"""
import json, os, sys
from datetime import datetime, timezone

ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
INDEX = ("data/yahoo/NSEI.parquet", "data/yahoo/NSEI.parquet")
OUT = "docs/whatif.json"
TOP_STOCKS = 800        # by traded value, so the list is the ones people actually look at
MISS_WINDOWS = (5, 10, 20, 30)


def month_name(iso):
    try:
        y, m, _ = str(iso)[:10].split("-")
        return "%s %s" % (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                           "Oct", "Nov", "Dec"][int(m) - 1], y)
    except Exception:
        return str(iso)[:10]


def main():
    import duckdb

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "drawdowns": {}, "nifty": None, "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive, so nothing can be computed."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("whatif: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1300MB'")
    con.execute("SET preserve_insertion_order=false")

    # ---- 1. worst peak-to-trough per stock, on liquid names ----
    # A running max gives the peak; the largest (peak - close)/peak is the worst fall.
    # DuckDB does this without pandas holding 3.5M rows.
    rows = con.execute("""
      WITH base AS (
        SELECT symbol, CAST(date AS VARCHAR) AS d, close,
               COALESCE(volume * close, 0) AS turnover
        FROM read_parquet(?)
        WHERE close > 0
      ),
      liquid AS (
        SELECT symbol FROM base GROUP BY symbol
        HAVING SUM(turnover) > 0 ORDER BY SUM(turnover) DESC LIMIT ?
      ),
      run AS (
        SELECT b.symbol, b.d, b.close,
               MAX(b.close) OVER w AS peak,
               -- arg_max gives the DATE of the running peak in the same pass. The earlier
               -- version looked the peak value up in a second query and matched the wrong
               -- row, so both dates came back as the trough's year.
               arg_max(b.d, b.close) OVER w AS peak_date
        FROM base b JOIN liquid l USING (symbol)
        WINDOW w AS (PARTITION BY b.symbol ORDER BY b.d
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
      )
      SELECT symbol, d, close, peak, peak_date,
             ROUND(100.0 * (close - peak) / peak, 2) AS dd
      FROM run
      WHERE peak > 0
      QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY dd ASC) = 1
    """, [arch, TOP_STOCKS]).fetchall()

    con.close()

    dd = {}
    for sym, trough_d, close, peak, peak_d, pct in rows:
        if pct is None or pct >= -5:
            continue
        dd[sym] = {
            "pct": round(float(pct), 2),
            "peak_date": str(peak_d)[:10] if peak_d else None,
            "trough_date": str(trough_d)[:10],
            "from": month_name(peak_d or ""),
            "to": month_name(trough_d),
            # what Rs 1,00,000 becomes if the same fall repeats from today
            "lakh_becomes": round(100000 * (1 + float(pct) / 100.0)),
        }
    out["drawdowns"] = dd
    print("  drawdowns: %d stocks (worst %.1f%%)"
          % (len(dd), min((v["pct"] for v in dd.values()), default=0)))

    # ---- 2. missing the best days on the index ----
    idx = None
    for p in ("data/yahoo/NSEI.parquet",):
        if os.path.exists(p):
            idx = p
            break
    if idx:
        try:
            import pandas as pd
            y = pd.read_parquet(idx)
            dcol = next((c for c in ("date", "Date") if c in y.columns), None)
            ccol = next((c for c in ("close", "Close") if c in y.columns), None)
            if dcol and ccol:
                y = y[[dcol, ccol]].dropna().rename(columns={dcol: "date", ccol: "close"})
                y["date"] = y["date"].astype(str).str[:10]
                y = y.sort_values("date").reset_index(drop=True)
                y["ret"] = y["close"].pct_change()
                y = y.dropna(subset=["ret"])

                # compound the returns, not last/first. `y` has already had its first row
                # dropped (it carried the NaN return), so last/first silently loses day one.
                total = ((1 + y["ret"]).prod() - 1) * 100
                best = y.nlargest(30, "ret")[["date", "ret"]]
                missing = {}
                for n in MISS_WINDOWS:
                    drop = set(best.head(n)["date"])
                    kept = y[~y["date"].isin(drop)]
                    # chain the remaining returns
                    growth = (1 + kept["ret"]).prod()
                    missing[str(n)] = round((growth - 1) * 100, 2)

                out["nifty"] = {
                    "from": y["date"].iloc[0],
                    "to": y["date"].iloc[-1],
                    "sessions": int(len(y)),
                    "total_return_pct": round(float(total), 2),
                    "missing_best": missing,
                    "best_days": [{"date": r.date, "pct": round(float(r.ret) * 100, 2)}
                                  for r in best.head(10).itertuples(index=False)],
                }
                print("  nifty %s -> %s: total %+.1f%% | missing 10 best: %+.1f%%"
                      % (y["date"].iloc[0], y["date"].iloc[-1], total,
                         missing.get("10", 0)))
        except Exception as e:
            print("  index unavailable: %s: %s" % (type(e).__name__, str(e)[:80]))
    else:
        print("  no Nifty series - the missing-days section is omitted")

    out["count"] = len(dd) + (1 if out["nifty"] else 0)
    out["note"] = ("Worst peak-to-trough fall per stock, with the dates, and what the index "
                   "return becomes if you miss its best days. Illustrations of volatility, "
                   "not strategies.")
    out["cautions"] = {
        "adjusted": "Split and bonus adjusted, so a 1:10 split is not a 90% fall.",
        "survivorship": ("Only stocks listed today are included. Delisted names are missing, "
                         "which makes past falls look milder than they were."),
        "missing_days": ("Assumes you held throughout and simply missed those days. It shows "
                         "how concentrated returns are, not a timing strategy."),
        "not_advice": "Past drawdowns do not predict future ones.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for sym in ("RELIANCE", "TCS", "HDFCBANK"):
        if sym in dd:
            v = dd[sym]
            print("   %-10s %.1f%%  %s -> %s  | Rs 1L becomes Rs %s"
                  % (sym, v["pct"], v["from"], v["to"], format(v["lakh_becomes"], ",")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
