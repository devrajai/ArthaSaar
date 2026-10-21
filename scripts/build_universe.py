#!/usr/bin/env python3
"""
build_universe.py - the FULL list of NSE-listed stocks, with what we already know.

Why this exists
  Fetching two years of daily history for ~2,600 symbols through Yahoo is hours of
  requests and gets rate-limited long before it finishes. So the site is tiered:

    tier 1  every listed symbol, immediately - symbol, company, series, ISIN, face value,
            plus the last close / change / volume from the NSE bhavcopy we already hold.
    tier 2  the deep page (chart + technicals + fundamentals), filled in progressively
            by build_stock_pages.py --rotate, which covers a slice each run.

  That way the list is complete on day one and the detail catches up, instead of
  nothing being available until every symbol is fetched.

Sources (free, no key):
  data/nse/symbol_master.csv   NSE EQUITY_L.csv - every listed symbol + ISIN
  data/csv/cm/cm_*.csv         NSE cash bhavcopy - last close, change, volume

Output: docs/universe.json
  {"updated": "...", "count": 2608,
   "rows": [ {symbol,name,series,isin,face,close,chg_pct,volume,date}, ... ]}

Usage:
  python scripts/build_universe.py
  python scripts/build_universe.py --limit 0      # 0 = no limit
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass


def load_master(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, dtype=str)
    # NSE ships the columns with leading spaces in the header
    df.columns = [c.strip() for c in df.columns]
    ren = {"SYMBOL": "symbol", "NAME OF COMPANY": "name", "SERIES": "series",
           "ISIN NUMBER": "isin", "FACE VALUE": "face", "DATE OF LISTING": "listed",
           "MARKET LOT": "lot"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    keep = [c for c in ("symbol", "name", "series", "isin", "face", "listed", "lot") if c in df.columns]
    df = df[keep].fillna("")
    df["symbol"] = df["symbol"].astype(str).str.strip()
    return df


def latest_bhavcopy() -> dict:
    """Last close / change / volume per symbol from the newest cash bhavcopy."""
    files = sorted(glob.glob("data/csv/cm/cm_*.csv"))
    if not files:
        return {}
    try:
        df = pd.read_csv(files[-1], dtype=str)
    except Exception:
        return {}
    df.columns = [c.strip().lower() for c in df.columns]
    # UDiFF names: tckrsymb, clscprc, prvsclsgprc, ttltrfqty; legacy: SYMBOL, CLOSE, ...
    symcol = next((c for c in ("tckrsymb", "symbol") if c in df.columns), None)
    closecol = next((c for c in ("clscprc", "close", "close_price") if c in df.columns), None)
    prevcol = next((c for c in ("prvsclsgprc", "prevclose", "prev_close") if c in df.columns), None)
    volcol = next((c for c in ("ttltrfqty", "totaltradedquantity", "volume") if c in df.columns), None)
    if not symcol or not closecol:
        return {}
    out = {}
    for _, r in df.iterrows():
        try:
            close = float(str(r[closecol]).replace(",", ""))
        except Exception:
            continue
        prev = None
        if prevcol:
            try:
                prev = float(str(r[prevcol]).replace(",", ""))
            except Exception:
                prev = None
        vol = None
        if volcol:
            try:
                vol = float(str(r[volcol]).replace(",", ""))
            except Exception:
                vol = None
        out[str(r[symcol]).strip()] = {
            "close": round(close, 2),
            "chg_pct": round((close / prev - 1) * 100, 2) if prev else None,
            "volume": int(vol) if vol else None,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Full listed-stock universe -> docs/universe.json")
    ap.add_argument("--master", default="data/nse/symbol_master.csv")
    ap.add_argument("--out", default="docs/universe.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--deep", default="docs/stocks.json", help="used to flag which have a full page")
    args = ap.parse_args()

    master = load_master(args.master)
    if master.empty:
        print(f"no symbol master at {args.master} - run scripts/fetch_nse_extra.py --only symbol_master")
        return 0

    quotes = latest_bhavcopy()
    print(f"master: {len(master)} symbols | bhavcopy quotes: {len(quotes)}")

    # which symbols already have a deep page
    deep = set()
    try:
        s = json.loads(Path(args.deep).read_text())
        deep = {v.get("symbol") for v in (s.get("stocks") or {}).values()}
    except Exception:
        pass

    rows = []
    for _, r in master.iterrows():
        sym = r["symbol"]
        q = quotes.get(sym, {})
        rows.append({
            "symbol": sym,
            "name": r.get("name", ""),
            "series": r.get("series", ""),
            "isin": r.get("isin", ""),
            "face": r.get("face", ""),
            "close": q.get("close"),
            "chg_pct": q.get("chg_pct"),
            "volume": q.get("volume"),
            "deep": sym in deep,
        })
    if args.limit:
        rows = rows[:args.limit]

    # listed ones with a price first, then alphabetical
    rows.sort(key=lambda x: (x["close"] is None, x["symbol"]))

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(rows),
        "with_price": sum(1 for r in rows if r["close"] is not None),
        "with_deep": sum(1 for r in rows if r["deep"]),
        "rows": rows,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)")
    print(f"  {payload['count']} listed symbols, {payload['with_price']} with a price, "
          f"{payload['with_deep']} with a full page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
