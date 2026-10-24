#!/usr/bin/env python3
"""
build_indicators.py - run the indicator library across the whole candle archive.

Reads a candles parquet (auto-detects data/candles/daily.parquet or cm_daily.parquet)
and writes:

  data/indicators/latest.parquet     one row per symbol: the most recent indicator set
                                     (a screen-ready snapshot - sort/filter on it)
  data/indicators/<symbol>.parquet   full indicator history per symbol (with --history)

Uses indicators.py, which is verified by test_indicators.py (independent recomputation
+ a no-look-ahead truncation test).

Note on adjusted prices: the candle archive is built from the raw bhavcopy, so splits
and bonuses show up as huge one-day gaps. Indicators like RSI/ATR will read those as
real moves. Adjust for corporate actions before trusting signals across such an event.

Usage
-----
  python scripts/build_indicators.py
  python scripts/build_indicators.py --history
  python scripts/build_indicators.py --in data/candles/cm_daily.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive import pick_candles, read_candles, add_window_arg  # noqa: E402
from indicators import add_all  # noqa: E402

KEY_COLS = ["symbol", "date", "close", "rsi_14", "sma_20", "sma_50", "sma_200",
            "ema_21", "macd", "macd_signal", "bb_pctb", "atr_pct", "adx",
            "stoch_k", "supertrend", "st_dir", "obv", "vwap"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute indicators across the candle archive.")
    ap.add_argument("--in", dest="infile", default="",
                    help="candles parquet (default: auto-detect)")
    ap.add_argument("--out", default="data/indicators")
    ap.add_argument("--history", action="store_true", help="also write per-symbol history")
    add_window_arg(ap)
    args = ap.parse_args()

    if not args.infile:
        args.infile = pick_candles()
    src = Path(args.infile) if args.infile else None
    if src is None or not src.exists():
        print("no candle archive found - skipping (run candles_from_bhavcopy.py or candles_from_drive.py)")
        return 0

    df = read_candles(src, getattr(args, "window", 500))
    need = {"symbol", "high", "low", "close", "volume"}
    missing = need - set(df.columns)
    if missing:
        print(f"candles missing columns: {missing} - skipping")
        return 0
    sortcol = "ts" if "ts" in df.columns else "date"
    print(f"indicators from {src}  |  {df['symbol'].nunique()} symbols")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.history:
        (out / "history").mkdir(exist_ok=True)

    snapshots = []
    for sym, g in df.groupby("symbol", sort=False):
        g = g.sort_values(sortcol)
        if len(g) < 20:            # too short for a meaningful indicator set
            continue
        enriched = add_all(g)
        if args.history:
            enriched.to_parquet(out / "history" / f"{sym}.parquet", index=False)
        last = enriched.tail(1).copy()
        last["symbol"] = sym
        if "date" not in last.columns and "ts" in last.columns:
            last["date"] = pd.to_datetime(last["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
        snapshots.append(last)

    if not snapshots:
        print("no symbol had enough history - nothing written")
        return 0

    latest = pd.concat(snapshots, ignore_index=True)
    cols = [c for c in KEY_COLS if c in latest.columns]
    dest = out / "latest.parquet"
    latest.to_parquet(dest, index=False)
    latest[cols].to_csv(out / "latest.csv", index=False)

    print(f"Wrote {dest}  ({len(latest)} symbols x {latest.shape[1]} columns)")
    print(f"  + {out}/latest.csv (key columns only)")
    if args.history:
        print(f"  + {out}/history/<symbol>.parquet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
