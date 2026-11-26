#!/usr/bin/env python3
"""
build_long_history.py - 5 and 10 year monthly closes, as one small JSON for the site.

The site's series.json carries 120 daily closes - about six months. That is enough for a
sparkline and useless for "how has this done over five years, against the Nifty". This pulls
monthly bars from Yahoo (via yfinance) and writes a compact file the detail windows can draw.

Scope is deliberately small. Every extra symbol is another Yahoo request, Yahoo rate-limits
without warning, and the page only needs enough to answer "how did this do" for the names a
reader is likely to open: the indices, the Nifty 50, and the largest names in the screener.

Usage
-----
  python scripts/build_long_history.py
  python scripts/build_long_history.py --years 10 --limit 300
  python scripts/build_long_history.py --symbols RELIANCE.NS TCS.NS

Output: docs/long_history.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/long_history.json"
SCREENER = "docs/screener.json"
INDICES = "docs/indices.json"

# Always included: the benchmarks a comparison needs, plus the commodity and FX references.
ALWAYS = ["^NSEI", "^NSEBANK", "^BSESN", "GC=F", "SI=F", "INR=X", "BTC-USD"]


def _load(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None


def pick_symbols(limit: int) -> list[str]:
    syms = list(ALWAYS)
    ix = _load(INDICES) or {}
    for i in (ix.get("indices") or []):
        if i.get("id") == "nifty50":
            for c in (i.get("constituents") or []):
                s = c.get("symbol")
                if s:
                    syms.append(s + ".NS")
            break
    scr = _load(SCREENER) or {}
    rows = sorted((scr.get("rows") or []),
                  key=lambda r: -(r.get("mcap") or r.get("turnover") or 0))
    for r in rows:
        s = r.get("symbol")
        if s:
            syms.append(s + ".NS")
        if len(syms) >= limit:
            break
    seen, out = set(), []
    for s in syms:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="5/10-year monthly closes for the site.")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--limit", type=int, default=260)
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except Exception as e:
        print(f"yfinance unavailable ({type(e).__name__}) - skipping")
        return 0

    syms = args.symbols or pick_symbols(args.limit)
    print(f"fetching {len(syms)} symbol(s), {args.years}y monthly")

    period = f"{args.years}y"
    series, failed = {}, []
    for i, sym in enumerate(syms, 1):
        try:
            df = yf.download(sym, period=period, interval="1mo",
                             progress=False, auto_adjust=True, threads=False)
            if df is None or df.empty:
                failed.append(sym)
                continue
            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
            close = close.dropna()
            if len(close) < 6:
                failed.append(sym)
                continue
            series[sym] = {
                "d": [d.strftime("%Y-%m") for d in close.index],
                "c": [round(float(v), 2) for v in close.values],
            }
        except Exception as e:
            failed.append(sym)
            print(f"  {sym:16s} FAILED ({type(e).__name__})")
        if i % 25 == 0:
            print(f"  {i}/{len(syms)} ... kept {len(series)}")
        import time as _t
        _t.sleep(args.sleep)

    if not series:
        print("nothing fetched - leaving the existing file alone")
        return 0

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(series),
        "years": args.years,
        "interval": "1mo",
        "note": ("Monthly closes from Yahoo Finance (unofficial, delayed, not a licensed feed). "
                 "Auto-adjusted for splits and dividends, so a 10-year line is comparable with "
                 "today's price. Enough to answer 'how did this do' - not a tick history."),
        "failed": failed[:40],
        "series": series,
    }
    Path(args.out).write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    size = Path(args.out).stat().st_size
    print(f"\n-> {args.out}  {size/1024:.0f} KB | {len(series)} symbols, {len(failed)} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
