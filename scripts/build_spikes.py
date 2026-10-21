#!/usr/bin/env python3
"""
build_spikes.py - find OI spikes (F&O) and volume spikes (cash).

OI spikes    from the NSE F&O bhavcopy: stock-futures rows where open interest moved
             sharply vs its own level (oi_change / oi), above a minimum OI floor so
             tiny contracts do not dominate.
Volume spike from the candle archive: today's volume against the symbol's own trailing
             average, so it is relative to that stock, not to the market.

Outputs:
  data/spikes/oi_spikes.csv
  data/spikes/volume_spikes.csv

Usage:
  python scripts/build_spikes.py
  python scripts/build_spikes.py --oi-pct 15 --vol-x 3
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

STOCK_FUT = {"STF", "FUTSTK"}


def oi_spikes(oi_pct: float, min_oi: float, rows: int) -> pd.DataFrame:
    csvs = sorted(glob.glob("data/csv/fo/fo_*.csv"))
    if not csvs:
        return pd.DataFrame()
    df = pd.read_csv(csvs[-1], dtype=str)
    if not {"instrm_type", "symbol", "oi", "oi_change"}.issubset(df.columns):
        return pd.DataFrame()
    fut = df[df["instrm_type"].isin(STOCK_FUT)].copy()
    for c in ("oi", "oi_change", "close", "prevclose"):
        if c in fut.columns:
            fut[c] = pd.to_numeric(fut[c], errors="coerce")
    fut = fut.dropna(subset=["oi", "oi_change"])
    fut = fut[fut["oi"] >= min_oi]
    fut["oi_pct"] = (fut["oi_change"] / fut["oi"].replace(0, pd.NA) * 100).round(2)
    fut["price_chg"] = ((fut["close"] / fut["prevclose"].replace(0, pd.NA) - 1) * 100).round(2)
    fut["date"] = df["date"].iloc[0] if "date" in df.columns and len(df) else ""
    out = fut[fut["oi_pct"].abs() >= oi_pct].copy()
    out["direction"] = out["oi_pct"].apply(lambda v: "build-up" if v > 0 else "unwind")
    cols = [c for c in ["date", "symbol", "oi", "oi_change", "oi_pct", "price_chg", "direction"] if c in out.columns]
    return out[cols].sort_values("oi_pct", key=lambda s: s.abs(), ascending=False).head(rows)


def volume_spikes(vol_x: float, lookback: int, rows: int) -> pd.DataFrame:
    src = ""
    for cand in ("data/candles/daily_adj.parquet", "data/candles/cm_daily_adj.parquet",
                 "data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
        if Path(cand).exists():
            src = cand
            break
    if not src:
        return pd.DataFrame()
    df = pd.read_parquet(src)
    if not {"symbol", "volume", "close"}.issubset(df.columns):
        return pd.DataFrame()
    sortcol = "ts" if "ts" in df.columns else "date"
    df = df.sort_values(["symbol", sortcol])
    g = df.groupby("symbol", sort=False)
    df["vol_avg"] = g["volume"].transform(lambda s: s.rolling(lookback).mean())
    df["vol_x"] = (df["volume"] / df["vol_avg"].replace(0, pd.NA)).round(2)
    df["chg"] = (g["close"].pct_change() * 100).round(2)
    last = df.groupby("symbol", sort=False).tail(1)
    out = last.dropna(subset=["vol_x"])
    out = out[out["vol_x"] >= vol_x]
    keep = [c for c in ["symbol", "date", "close", "chg", "volume", "vol_avg", "vol_x"] if c in out.columns]
    return out[keep].sort_values("vol_x", ascending=False).head(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="OI and volume spike detection.")
    ap.add_argument("--oi-pct", type=float, default=12.0, help="min |oi_change/oi| %% for an OI spike")
    ap.add_argument("--min-oi", type=float, default=100_000, help="ignore contracts below this OI")
    ap.add_argument("--vol-x", type=float, default=2.5, help="volume multiple of its own average")
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--rows", type=int, default=25)
    ap.add_argument("--out", default="data/spikes")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    oi = oi_spikes(args.oi_pct, args.min_oi, args.rows)
    if len(oi):
        oi.to_csv(out / "oi_spikes.csv", index=False)
        print(f"OI spikes     : {len(oi)} (|oi change| >= {args.oi_pct}% of OI, oi >= {args.min_oi:,.0f})")
    else:
        print("OI spikes     : none (no F&O bhavcopy, or nothing crossed the threshold)")

    vol = volume_spikes(args.vol_x, args.lookback, args.rows)
    if len(vol):
        vol.to_csv(out / "volume_spikes.csv", index=False)
        print(f"Volume spikes : {len(vol)} (>= {args.vol_x}x its own {args.lookback}-day average)")
    else:
        print("Volume spikes : none (the candle archive needs >= "
              f"{args.lookback} days per symbol before this can work)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
