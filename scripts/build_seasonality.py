#!/usr/bin/env python3
"""Stock seasonality (Task 2) - which months a stock has historically been strong in.

A seasonal pattern needs YEARS of monthly returns. Two years is noise, so this refuses to
publish a pattern from less than three. The check runs on real data, so the moment the
candle archive has enough history the tab fills in by itself.
"""
import json, os, sys, glob
from datetime import datetime, timezone
from collections import defaultdict

OUT = "docs/seasonality.json"
MIN_YEARS = 3
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_history():
    """Monthly closes per symbol from the candle archive, if it is deep enough.

    Returns {symbol: {year: {month: close}}}. Empty when there is no usable archive.
    """
    # daily.parquet is the 5-year archive restored from Drive; cm_daily.parquet is only the
    # few days built from bhavcopy. This hardcoded cm_daily, so seasonality could never see
    # enough history to publish - it was reading the shallow file the whole time.
    path = None
    for cand in ("data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
        if os.path.exists(cand):
            path = cand
            break
    if not path:
        return {}
    print("  reading %s" % path)
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        if "date" not in df.columns or "symbol" not in df.columns:
            return {}
        df = df[["symbol", "date", "close"]].dropna()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        if df["date"].dt.to_period("M").nunique() < MIN_YEARS * 12:
            print("  archive covers only %d months" % df["date"].dt.to_period("M").nunique())
            return {}
        hist = defaultdict(lambda: defaultdict(dict))
        for (sym, per), grp in df.groupby([df["symbol"], df["date"].dt.to_period("M")]):
            hist[sym][per.year][per.month] = float(grp["close"].iloc[-1])
        return hist
    except Exception as e:
        print("  archive -> %s" % type(e).__name__)
        return {}


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "months": MONTHS, "rows": [], "count": 0, "min_years": MIN_YEARS, "note": ""}
    hist = load_history()
    if not hist:
        out["note"] = ("Not enough history yet. A seasonal pattern needs at least %d years of "
                       "monthly closes and the stored archive is shallower than that, so "
                       "nothing is shown rather than a pattern read out of noise." % MIN_YEARS)
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("seasonality: skipped (insufficient history)")
        return 0

    rows = []
    for sym, years in hist.items():
        if len(years) < MIN_YEARS:
            continue
        bymonth = defaultdict(list)
        prev_dec = None
        for yr in sorted(years):
            months = years[yr]
            for m in range(1, 13):
                # January's "previous month" is December of the PREVIOUS YEAR. The old code
                # did months.get(12) on the same year, which is eleven months LATER - so
                # every January figure measured the year backwards.
                prev = prev_dec if m == 1 else months.get(m - 1)
                cur = months.get(m)
                if prev and cur:
                    bymonth[m].append((cur / prev - 1.0) * 100.0)
            prev_dec = months.get(12)
        if len(bymonth) < 12:
            continue
        avgs = [round(sum(bymonth[m]) / len(bymonth[m]), 2) if bymonth[m] else None for m in range(1, 13)]
        if all(v is None for v in avgs):
            continue
        rows.append({"symbol": sym, "months": avgs, "years": len(years)})
    rows.sort(key=lambda r: r["symbol"])
    out["rows"], out["count"] = rows, len(rows)
    out["note"] = ("Average monthly return by calendar month, over at least %d years. "
                   "Seasonality is a weak, backward-looking effect - it is context, not a "
                   "reason to buy." % MIN_YEARS)
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("seasonality: %d symbols -> %s" % (len(rows), OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
