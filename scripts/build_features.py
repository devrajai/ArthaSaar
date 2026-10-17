#!/usr/bin/env python3
"""
build_features.py - turn the candle archive into a model-ready table.

Reads a candles parquet (auto-detects data/candles/daily.parquet or cm_daily.parquet)
and writes data/training/features.parquet: one row per symbol per day, with engineered
features and a forward-return label.

Features (all computed per symbol, no look-ahead):
  ret_1, ret_5, ret_20      trailing returns
  sma20_ratio, sma50_ratio  close / SMA
  vol_20                    std-dev of daily returns over 20d (realised vol)
  rsi_14                    Wilder RSI
  range_pct                 (high-low)/close
  vol_z                     volume z-score vs 20d mean
Labels:
  fwd_ret_1                 next-day return  (regression target)
  fwd_up_1                  1 if next-day return > 0 (classification target)

Honest note: this is a feature table, not a model. What you train on it, and how you
validate it (walk-forward, not a random split - markets are time-ordered), decides
whether it is any good. Past patterns do not guarantee future ones.

Computed with groupby transforms (not one frame per symbol) so it stays cheap on
thousands of symbols.

Usage
-----
  python scripts/build_features.py
  python scripts/build_features.py --in data/candles/cm_daily.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# Cap Arrow's thread pool. Some containers (CI, sandboxes) have a low thread limit and
# pyarrow's default pool can fail with "Failed to launch worker thread".
try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

FEATURES = ["ret_1", "ret_5", "ret_20", "sma20_ratio", "sma50_ratio",
            "vol_20", "rsi_14", "range_pct", "vol_z"]
LABELS = ["fwd_ret_1", "fwd_up_1"]


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    roll_dn = down.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    sortcol = "ts" if "ts" in df.columns else "date"
    df = df.sort_values(["symbol", sortcol]).copy()
    c = df["close"]

    # trailing returns
    df["ret_1"] = df.groupby("symbol", sort=False)["close"].pct_change(1)
    df["ret_5"] = df.groupby("symbol", sort=False)["close"].pct_change(5)
    df["ret_20"] = df.groupby("symbol", sort=False)["close"].pct_change(20)

    # moving-average ratios
    df["sma20_ratio"] = c / df.groupby("symbol", sort=False)["close"].transform(
        lambda s: s.rolling(20).mean())
    df["sma50_ratio"] = c / df.groupby("symbol", sort=False)["close"].transform(
        lambda s: s.rolling(50).mean())

    # realised vol + RSI + range
    df["vol_20"] = df.groupby("symbol", sort=False)["ret_1"].transform(
        lambda s: s.rolling(20).std())
    df["rsi_14"] = df.groupby("symbol", sort=False)["close"].transform(rsi)
    df["range_pct"] = (df["high"] - df["low"]) / c.replace(0, np.nan)

    # volume z-score
    vm = df.groupby("symbol", sort=False)["volume"].transform(lambda s: s.rolling(20).mean())
    vs = df.groupby("symbol", sort=False)["volume"].transform(lambda s: s.rolling(20).std())
    df["vol_z"] = (df["volume"] - vm) / vs.replace(0, np.nan)

    # forward labels (shift within each symbol - no cross-symbol bleed)
    df["fwd_ret_1"] = df.groupby("symbol", sort=False)["close"].shift(-1) / c - 1
    df["fwd_up_1"] = (df["fwd_ret_1"] > 0).astype("float")
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a model-ready feature table from candles.")
    ap.add_argument("--in", dest="infile", default="",
                    help="candles parquet (default: auto-detect daily.parquet or cm_daily.parquet)")
    ap.add_argument("--out", default="data/training/features.parquet")
    ap.add_argument("--min-days", type=int, default=200,
                    help="skip if no symbol has this much history")
    args = ap.parse_args()

    if not args.infile:
        for cand in ("data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
            if Path(cand).exists():
                args.infile = cand
                break
    src = Path(args.infile) if args.infile else None
    if src is None or not src.exists():
        print("no candle archive found - skipping (run candles_from_bhavcopy.py or candles_from_drive.py)")
        return 0
    print(f"features from {src}")

    df = pd.read_parquet(src)
    need = {"symbol", "high", "low", "close", "volume"}
    missing = need - set(df.columns)
    if missing:
        print(f"candles missing columns: {missing} - skipping")
        return 0
    if "ts" not in df.columns and "date" not in df.columns:
        print("candles need a 'ts' or 'date' column - skipping")
        return 0

    out = build_features(df)
    out = out.dropna(subset=FEATURES + ["fwd_ret_1"]).reset_index(drop=True)
    if out.empty:
        print(f"not enough history yet (need ~{args.min_days} days/symbol) - skipping")
        return 0

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dest, index=False)

    print(f"Wrote {dest}")
    print(f"  rows: {len(out):,}  symbols: {out['symbol'].nunique()}  "
          f"window: {out['date'].min()} -> {out['date'].max()}")
    print(f"  features: {', '.join(FEATURES)}")
    print(f"  labels:   {', '.join(LABELS)}")
    print(f"  base rate (next-day up): {out['fwd_up_1'].mean():.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
