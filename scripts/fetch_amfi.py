#!/usr/bin/env python3
"""
fetch_amfi.py - mutual fund NAVs from AMFI (free, no key, no login).

AMFI publishes every scheme's latest NAV as one plain text file - the official source
for Indian mutual fund NAVs. This also fills the "MF" gap: the hub had equities, F&O,
indices and crypto but no mutual funds.

  https://www.amfiindia.com/spages/NAVAll.txt

Format:  SchemeCode;ISIN_Payout;ISIN_Reinvest;SchemeName;NAV;Date
Sections are separated by fund-house header lines, which are skipped.

Note: AMFI is not reachable from every network (some CI/proxy environments block it),
so a failure is reported and skipped rather than treated as an error.

Usage
-----
  python scripts/fetch_amfi.py
  python scripts/fetch_amfi.py --out data/amfi
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

NAVALL = "https://www.amfiindia.com/spages/NAVAll.txt"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}


def parse_navall(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        parts = line.split(";")
        if len(parts) < 6:
            continue                      # fund-house header or blank
        code = parts[0].strip()
        if not code.isdigit():
            continue
        rows.append({
            "scheme_code": code,
            "isin_growth": parts[1].strip(),
            "isin_reinvest": parts[2].strip(),
            "scheme_name": parts[3].strip(),
            "nav": parts[4].strip(),
            "date": parts[5].strip(),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch AMFI mutual-fund NAVs.")
    ap.add_argument("--out", default="data/amfi")
    ap.add_argument("--url", default=NAVALL)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(args.url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"AMFI unreachable ({type(e).__name__}: {str(e)[:60]}) - skipping. "
              "This is common behind proxies; it works from most CI runners.")
        return 0

    df = parse_navall(raw)
    if df.empty:
        print("AMFI returned no parseable rows - format may have changed")
        return 0

    df.to_csv(out / "nav_all.csv", index=False)
    try:
        df.to_parquet(out / "nav_all.parquet", index=False)
    except Exception:
        pass
    latest = df["date"].max()
    print(f"AMFI: {len(df):,} schemes  |  latest NAV date {latest.date() if pd.notna(latest) else '?'}")
    print(f"  {df['scheme_name'].nunique():,} distinct scheme names")
    print(f"Wrote {out}/nav_all.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
