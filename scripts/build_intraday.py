#!/usr/bin/env python3
"""
build_intraday.py - recent 5-minute bars for the detail-window timeframe switch.

Yahoo keeps 5-minute bars for about 60 days and 1-minute for about 7, so this is a rolling
recent window, not an archive. It writes the 5-minute bars only; 15- and 30-minute are resampled
in the browser, which is a third of the file size and the same information.

Usage
-----
  python scripts/build_intraday.py                    # Nifty 50 + indices, 5 sessions
  python scripts/build_intraday.py --days 10 --limit 120

Output: docs/intraday_recent.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/intraday_recent.json"
INDICES = "docs/indices.json"
SCREENER = "docs/screener.json"
ALWAYS = ["^NSEI", "^NSEBANK", "^BSESN"]


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def pick(limit):
    syms = list(ALWAYS)
    ix = _load(INDICES) or {}
    for i in (ix.get("indices") or []):
        if i.get("id") == "nifty50":
            syms += [(c.get("symbol") or "") + ".NS" for c in (i.get("constituents") or []) if c.get("symbol")]
            break
    scr = _load(SCREENER) or {}
    for r in sorted((scr.get("rows") or []), key=lambda r: -(r.get("mcap") or r.get("turnover") or 0)):
        if r.get("symbol"):
            syms.append(r["symbol"] + ".NS")
        if len(syms) >= limit:
            break
    seen, out = set(), []
    for s in syms:
        if s and s not in seen:
            seen.add(s); out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except Exception:
        print("yfinance unavailable - skipping")
        return 0

    syms = pick(args.limit)
    period = f"{max(1, args.days)}d"
    print(f"fetching {len(syms)} symbol(s), {period} at 5m")

    series, failed = {}, []
    for i, sym in enumerate(syms, 1):
        try:
            df = yf.download(sym, period=period, interval="5m", progress=False,
                             auto_adjust=True, threads=False)
            if df is None or df.empty:
                failed.append(sym); continue
            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
            close = close.dropna()
            if len(close) < 10:
                failed.append(sym); continue
            # unix seconds keep the payload small; the browser formats them
            series[sym] = {
                "t": [int(ts.timestamp()) for ts in close.index],
                "c": [round(float(v), 2) for v in close.values],
            }
        except Exception as e:
            failed.append(sym)
            print(f"  {sym:16s} FAILED ({type(e).__name__})")
        import time as _t; _t.sleep(args.sleep)
        if i % 20 == 0:
            print(f"  {i}/{len(syms)} kept {len(series)}")

    if not series:
        print("nothing fetched - leaving the existing file alone")
        return 0

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(series),
        "interval": "5m",
        "days": args.days,
        "note": ("5-minute bars from Yahoo Finance (unofficial, delayed, not a licensed feed). "
                 "Yahoo keeps 5-minute bars for about 60 days, so this is a rolling recent "
                 "window. 15- and 30-minute are resampled from these in the browser."),
        "failed": failed[:30],
        "series": series,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"\n-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(series)} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(main())
