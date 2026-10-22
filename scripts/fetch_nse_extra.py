#!/usr/bin/env python3
"""
fetch_nse_extra.py - free NSE reference data beyond the bhavcopy.

Pulls, each independently (one failing never blocks the rest):
  fii_dii        daily FII/DII cash flows        -> data/nse/fii_dii.csv
  symbol_master  every listed symbol + ISIN      -> data/nse/symbol_master.csv
  indices        index constituent lists         -> data/nse/index_<name>.csv
  announcements  corporate announcements         -> data/nse/announcements.csv

All free, no API key. NSE's /api/ endpoints need a session cookie, so this warms up on
the public pages first (same trick as nse_source.py).

Usage
-----
  python scripts/fetch_nse_extra.py
  python scripts/fetch_nse_extra.py --only fii_dii symbol_master
"""

from __future__ import annotations

import argparse
import io
import time
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
}
WARM = ["https://www.nseindia.com/",
        "https://www.nseindia.com/all-reports",
        "https://www.nseindia.com/companies-listing/corporate-filings-announcements"]

INDICES = {
    # broad market
    "nifty50":          "ind_nifty50list",
    "niftynext50":      "ind_niftynext50list",
    "nifty100":         "ind_nifty100list",
    "nifty200":         "ind_nifty200list",
    "nifty500":         "ind_nifty500list",
    "niftymidcap50":    "ind_niftymidcap50list",
    "niftymidcap150":   "ind_niftymidcap150list",
    "niftysmallcap50":  "ind_niftysmallcap50list",
    "niftysmallcap250": "ind_niftysmallcap250list",
    "niftymidsmallcap400": "ind_niftymidsmallcap400list",
    # sector indices
    "niftybank":        "ind_niftybanklist",
    "niftyit":          "ind_niftyitlist",
    "niftyauto":        "ind_niftyautolist",
    "niftyfmcg":        "ind_niftyfmcglist",
    "niftypharma":      "ind_niftypharmalist",
    "niftymetal":       "ind_niftymetallist",
    "niftyrealty":      "ind_niftyrealtylist",
    "niftyenergy":      "ind_niftyenergylist",
    "niftyinfra":       "ind_niftyinfralist",
    "niftymedia":       "ind_niftymedialist",
    "niftyfinancelist": "ind_niftyfinancelist",
    "niftypsubank":     "ind_niftypsubanklist",
    "niftyconsumerdur": "ind_niftyconsumerdurableslist",
    "niftyhealthcare":  "ind_niftyhealthcarelist",
    "niftyoilgas":      "ind_niftyoilgaslist",
    "niftychemicals":   "ind_niftychemicalslist",
    "niftycement":      "ind_niftycementlist",
    "niftytelecom":     "ind_niftytelecomlist",
}
SYMBOL_MASTER = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
FII_DII = "https://www.nseindia.com/api/fiidiiTradeReact"
ANNOUNCEMENTS = "https://www.nseindia.com/api/corporate-announcements?index=equities"


def session():
    import requests
    s = requests.Session()
    s.headers.update(UA)
    for w in WARM:
        try:
            s.get(w, timeout=25)
        except Exception:
            pass
    time.sleep(0.3)
    return s


def get_json(s, url):
    r = s.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def get_csv(s, url):
    r = s.get(url, timeout=30)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def main() -> int:
    ap = argparse.ArgumentParser(description="Free NSE reference data.")
    ap.add_argument("--out", default="data/nse")
    ap.add_argument("--only", nargs="*", default=None,
                    choices=["fii_dii", "symbol_master", "indices", "announcements"])
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    want = set(args.only) if args.only else {"fii_dii", "symbol_master", "indices", "announcements"}

    try:
        s = session()
    except Exception as e:
        print(f"could not start a session: {type(e).__name__}: {e}")
        return 0

    ok = fail = 0

    if "fii_dii" in want:
        try:
            rows = get_json(s, FII_DII)
            df = pd.DataFrame(rows)
            for c in ("buyValue", "sellValue", "netValue"):
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            df.to_csv(out / "fii_dii.csv", index=False)
            print(f"  fii_dii: {len(df)} row(s)  {df[['category','netValue']].to_dict('records') if len(df) else ''}")
            ok += 1
        except Exception as e:
            print(f"  fii_dii: FAILED {type(e).__name__}: {str(e)[:60]}"); fail += 1

    if "symbol_master" in want:
        try:
            df = get_csv(s, SYMBOL_MASTER)
            df.to_csv(out / "symbol_master.csv", index=False)
            print(f"  symbol_master: {len(df)} symbols, cols {list(df.columns)[:5]}")
            ok += 1
        except Exception as e:
            print(f"  symbol_master: FAILED {type(e).__name__}: {str(e)[:60]}"); fail += 1

    if "indices" in want:
        for name, stem in INDICES.items():
            try:
                url = f"https://nsearchives.nseindia.com/content/indices/{stem}.csv"
                df = get_csv(s, url)
                df.to_csv(out / f"index_{name}.csv", index=False)
                print(f"  index_{name}: {len(df)} constituents")
                ok += 1
            except Exception as e:
                print(f"  index_{name}: FAILED {type(e).__name__}: {str(e)[:50]}"); fail += 1

    if "announcements" in want:
        try:
            rows = get_json(s, ANNOUNCEMENTS)
            df = pd.DataFrame(rows)
            df.to_csv(out / "announcements.csv", index=False)
            print(f"  announcements: {len(df)} item(s)")
            ok += 1
        except Exception as e:
            print(f"  announcements: FAILED {type(e).__name__}: {str(e)[:60]}"); fail += 1

    print(f"\nNSE extra: {ok} ok, {fail} failed -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
