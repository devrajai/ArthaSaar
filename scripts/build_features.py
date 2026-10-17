#!/usr/bin/env python3
"""
build_features.py - turn the candle archive into a model-ready table.

Reads data/candles/daily.parquet (from candles_from_drive.py) and produces
data/training/features.parquet: one row per symbol per day, with engineered
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
validate it (walk-forward, not a random split - markets are time-ordered), is the
part that decides whether it is any good. Past patterns do not guarantee future ones.

Usage
-----
  python scripts/build_features.py --in data/candles/daily.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    roll_dn = down.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def features_for_symbol(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("ts").copy()
    c = g["close"]
    g["ret_1"] = c.pct_change(1)
    g["ret_5"] = c.pct_change(5)
    g["ret_20"] = c.pct_change(20)
    g["sma20_ratio"] = c / c.rolling(20).mean()
    g["sma50_ratio"] = c / c.rolling(50).mean()
    g["vol_20"] = g["ret_1"].rolling(20).std()
    g["rsi_14"] = rsi(c, 14)
    g["range_pct"] = (g["high"] - g["low"]) / c.replace(0, np.nan)
    vm = g["volume"].rolling(20).mean()
    vs = g["volume"].rolling(20).std().replace(0, np.nan)
    g["vol_z"] = (g["volume"] - vm) / vs
    g["fwd_ret_1"] = c.shift(-1) / c - 1
    g["fwd_up_1"] = (g["fwd_ret_1"] > 0).astype("float")
    return g


FEATURES = ["ret_1", "ret_5", "ret_20", "sma20_ratio", "sma50_ratio",
            "vol_20", "rsi_14", "range_pct", "vol_z"]
LABELS = ["fwd_ret_1", "fwd_up_1"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a model-ready feature table from candles.")
    ap.add_argument("--in", dest="infile", default="data/candles/daily.parquet")
    ap.add_argument("--out", default="data/training/features.parquet")
    args = ap.parse_args()

    src = Path(args.infile)
    if not src.exists():
        raise SystemExit(f"No candles at {src} - run candles_from_drive.py first.")
    df = pd.read_parquet(src)
    need = {"symbol", "ts", "high", "low", "close", "volume"}
    if not need.issubset(df.columns):
        raise SystemExit(f"candles missing columns: {need - set(df.columns)}")

    out = pd.concat([features_for_symbol(g) for _, g in df.groupby("symbol", sort=False)],
                    ignore_index=True)
    out = out.dropna(subset=FEATURES + ["fwd_ret_1"]).reset_index(drop=True)

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
