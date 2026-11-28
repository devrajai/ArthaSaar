#!/usr/bin/env python3
"""
build_index_periods.py - how each index moved between two dates.

The site could say where an index is today. It could not answer the question a newspaper table
answers every week: which sectors rose and which fell between two dates, and by how much.

This pulls two years of daily closes for the broad and sector indices from Yahoo and stores them
compactly, so any pair of dates can be compared in the browser without another fetch.

Usage
-----
  python scripts/build_index_periods.py
  python scripts/build_index_periods.py --period 3y

Output: docs/index_periods.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/index_periods.json"

# broad first, then sectors - the order the table reads in
INDICES = [
    ("^NSEI", "Nifty 50", "Broad"),
    ("^BSESN", "BSE Sensex", "Broad"),
    ("^NSEBANK", "Bank Nifty", "Broad"),
    ("^CNXIT", "Nifty IT", "Sector"),
    ("^CNXAUTO", "Nifty Auto", "Sector"),
    ("^CNXMETAL", "Nifty Metal", "Sector"),
    ("^CNXPHARMA", "Nifty Pharma", "Sector"),
    ("^CNXFMCG", "Nifty FMCG", "Sector"),
    ("^CNXREALTY", "Nifty Realty", "Sector"),
    ("^CNXENERGY", "Nifty Energy", "Sector"),
    ("^CNXPSUBANK", "Nifty PSU Bank", "Sector"),
    ("^CNXINFRA", "Nifty Infra", "Sector"),
    ("^CNXMEDIA", "Nifty Media", "Sector"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--period", default="2y")
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except Exception:
        print("yfinance unavailable - skipping")
        return 0

    out, failed = {}, []
    for sym, name, kind in INDICES:
        try:
            df = yf.Ticker(sym).history(period=args.period, interval="1d", auto_adjust=True)
            if df is None or df.empty or len(df) < 30:
                failed.append(sym)
                continue
            closes = df["Close"].dropna()
            out[sym] = {
                "name": name,
                "kind": kind,
                # parallel arrays keep the file small; dates are ISO strings
                "d": [d.strftime("%Y-%m-%d") for d in closes.index],
                "c": [round(float(v), 2) for v in closes.values],
            }
        except Exception as e:
            failed.append(sym)
            if len(failed) <= 4:
                print(f"  {sym:12s} FAILED ({type(e).__name__})")
        import time as _t; _t.sleep(args.sleep)

    if not out:
        print("nothing fetched - leaving the existing file alone")
        return 0

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(out),
        "note": ("Daily closes for the broad and sector indices, from Yahoo Finance. Enough to "
                 "compare any two dates. Prices are index levels, not returns; the comparison is "
                 "the change between the two closes the reader picks."),
        "failed": failed,
        "indices": out,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(out)} indices")
    for s, v in list(out.items())[:3]:
        print(f"   {v['name']:16s} {len(v['c'])} sessions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
