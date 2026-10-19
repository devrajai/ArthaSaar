#!/usr/bin/env python3
"""
fetch_yahoo.py - pull OHLCV history from Yahoo Finance via yfinance.

Covers what the NSE bhavcopy does not: global indices, FX, commodities, crypto, and
longer history for Indian names. Config lives in config/yahoo_symbols.json.

Honest limits (Yahoo has NO official API):
  * yfinance is an UNOFFICIAL wrapper. Yahoo rate-limits it and occasionally breaks it.
  * Data is delayed and not a licensed feed. Fine for research/backtesting, not for
    execution, and redistribution is restricted by Yahoo's terms.
  * Prefer the NSE bhavcopy for Indian equities - it is the exchange's own record.

Usage
-----
  python scripts/fetch_yahoo.py                       # everything in the config
  python scripts/fetch_yahoo.py --group indices
  python scripts/fetch_yahoo.py --symbols RELIANCE.NS TCS.NS --period 5y
  python scripts/fetch_yahoo.py --group crypto --interval 1wk

Output: data/yahoo/<safe_symbol>.parquet  and  data/yahoo/_all.parquet
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd

# Cap Arrow's thread pool. Some containers (CI, sandboxes) have a low thread limit and
# pyarrow's default pool can fail with "Failed to launch worker thread".
try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass


def _safe(sym: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_")


def _load_config(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"No config at {path}")
    return json.loads(path.read_text())


def _download(sym: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf  # lazy, so --help works without it
    except ImportError:
        print("  yfinance is not installed - run: pip install yfinance")
        return None
    for attempt in range(3):
        try:
            df = yf.download(sym, period=period, interval=interval,
                             progress=False, auto_adjust=True)
            if df is None or df.empty:
                raise RuntimeError("empty frame")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df["symbol"] = sym
            return df
        except Exception as e:  # noqa: BLE001
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                print(f"  {sym}: FAILED ({type(e).__name__}: {str(e)[:60]})")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Pull Yahoo Finance history via yfinance.")
    ap.add_argument("--config", default="config/yahoo_symbols.json")
    ap.add_argument("--group", default="", help="a group from the config (default: all)")
    ap.add_argument("--symbols", nargs="*", default=None, help="explicit symbols (overrides config)")
    ap.add_argument("--period", default="2y", help="1d/5d/1mo/6mo/1y/2y/5y/10y/max")
    ap.add_argument("--interval", default="1d", help="1d/1wk/1mo (1m-1h for short ranges)")
    ap.add_argument("--out", default="data/yahoo")
    ap.add_argument("--min-rows", type=int, default=50,
                    help="drop symbols returning fewer rows than this (bad tickers)")
    args = ap.parse_args()

    if args.symbols:
        syms = args.symbols
    else:
        groups = _load_config(Path(args.config)).get("groups", {})
        if args.group:
            syms = groups.get(args.group, [])
            if not syms:
                raise SystemExit(f"group '{args.group}' not in config (have: {list(groups)})")
        else:
            syms = [s for lst in groups.values() for s in lst]

    if not syms:
        raise SystemExit("no symbols to fetch")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"fetching {len(syms)} symbol(s) from Yahoo | period={args.period} interval={args.interval}")

    frames = []
    for sym in syms:
        df = _download(sym, args.period, args.interval)
        if df is None:
            continue
        if len(df) < args.min_rows:
            print(f"  {sym}: only {len(df)} rows - skipped (bad/renamed ticker?)")
            continue
        df.to_parquet(out / f"{_safe(sym)}.parquet", index=False)
        frames.append(df)
        print(f"  {sym}: {len(df)} rows")
        time.sleep(0.4)   # be polite - Yahoo rate-limits

    if frames:
        allf = pd.concat(frames, ignore_index=True)
        allf.to_parquet(out / "_all.parquet", index=False)
        print(f"\nWrote {len(frames)} file(s) + _all.parquet  |  {len(allf):,} rows, "
              f"{allf['symbol'].nunique()} symbols")
    else:
        print("nothing fetched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
