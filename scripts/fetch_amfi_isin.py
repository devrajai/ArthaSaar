#!/usr/bin/env python3
"""AMFI's full NAV file, kept for its ISINs.

WHY THIS EXISTS
build_etf_premium.py was matching NSE's ETF list to AMFI schemes by GUESSING at names.
NSE calls it "Nippon India ETF Nifty 50 BeES", AMFI calls it something else again, so the
matcher had to score tokens, require a distinctive one, and drop anything ambiguous - and
still only matched 2 of 356.

Both sides carry an ISIN. That is an exact key, so no guessing is needed:

  NSE  eq_etfseclist.csv  ->  Symbol, Underlying Asset, ..., ISINNumber, ...
  AMFI NAVAll.txt         ->  Code;ISIN Growth;ISIN Div Payout;Scheme Name;NAV;Date

This fetches AMFI's file and writes just the mapping we need. The pipeline can reach
amfiindia.com from GitHub's runners; it is only blocked from the build sandbox.

NOTE ON FORMAT: NAVAll.txt is semicolon-separated and contains section header lines that
are not data. Only rows whose first field is a numeric scheme code are kept, which is what
filters the headers out without hard-coding their text.
"""
import os, re, sys, urllib.request
from datetime import datetime, timezone

OUT = "data/amfi/navall.parquet"
URL = "https://www.amfiindia.com/spages/NAVAll.txt"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}


def fetch():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read().decode("utf-8", "replace")


def main():
    try:
        raw = fetch()
    except Exception as e:
        print("  AMFI unreachable (%s: %s)" % (type(e).__name__, str(e)[:90]))
        print("  -> leaving any existing mapping untouched")
        return 0
    print("  downloaded %s chars" % f"{len(raw):,}")

    try:
        import pandas as pd
    except Exception:
        print("  pandas unavailable")
        return 1

    rows = []
    for line in raw.splitlines():
        p = [x.strip() for x in line.split(";")]
        if len(p) < 6 or not re.fullmatch(r"\d{5,7}", p[0] or ""):
            continue                      # section header, not a scheme
        rows.append({
            "code": p[0],
            "isin_growth": p[1] if p[1] not in ("-", "") else None,
            "isin_div": p[2] if p[2] not in ("-", "") else None,
            "scheme": p[3],
            "nav": p[4],
            "date": p[5],
        })

    if not rows:
        print("  parsed 0 schemes - format may have changed; leaving the old file alone")
        return 1

    df = pd.DataFrame(rows)
    with_isin = int(df["isin_growth"].notna().sum() + df["isin_div"].notna().sum())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_parquet(OUT, index=False)
    print("  %s schemes, %s ISINs -> %s" % (f"{len(df):,}", f"{with_isin:,}", OUT))
    print("  sample:", df.iloc[0].to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
