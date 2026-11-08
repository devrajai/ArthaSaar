#!/usr/bin/env python3
"""
build_setup_history.py - what happened the last times this stock looked like this.

WHY THIS EXISTS
Every technical number on the site is a description of today. None of them says what
tended to follow. This turns each stock's own history into a base rate: find the days when
it had the same shape as now, and report what the next 5 and 20 sessions did, with the
number of cases attached.

THE CONDITION, AND WHY IT IS COARSE ON PURPOSE
Two things, both already computed for the stock pages:

    RSI(14) bucket   oversold <30 | weak 30-45 | mid 45-55 | strong 55-70 | overbought >70
    trend            above or below the 200-day average

Twenty cells per stock would be more precise and useless: 1,000 sessions split twenty ways
leaves 50 cases at best and often three. Ten cells keeps the sample large enough to mean
something, and the card hides anything under --min-cases rather than printing a number
built on four observations.

WHAT IT DOES NOT DO
It does not test whether the setup is any good across the market, only what this stock did
after it. Both are base rates, not forecasts, and a stock with 12 cases has 12 cases.

Input:  the candle archive (data/candles/*.parquet)
Output: docs/setup_history.json

Usage:
  python scripts/build_setup_history.py
  python scripts/build_setup_history.py --min-cases 10 --max-symbols 2500
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ARCHIVES = ("data/candles/daily_adj.parquet",
            "data/candles/cm_daily_adj.parquet",
            "data/candles/daily.parquet",
            "data/candles/cm_daily.parquet")
OUT = "docs/setup_history.json"
FWD = (5, 20)
RSI_BUCKETS = ((0, 30, "oversold"), (30, 45, "weak"), (45, 55, "mid"),
               (55, 70, "strong"), (70, 101, "overbought"))


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def bucket(r: float, above: bool) -> str | None:
    if not np.isfinite(r):
        return None
    for lo, hi, name in RSI_BUCKETS:
        if lo <= r < hi:
            return f"{name}|{'above' if above else 'below'}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-stock base rates for today's setup.")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--min-cases", type=int, default=8)
    ap.add_argument("--min-bars", type=int, default=260)
    ap.add_argument("--max-symbols", type=int, default=2500)
    args = ap.parse_args()

    arch = next((p for p in ARCHIVES if Path(p).exists()), None)
    if not arch:
        print("no candle archive on disk - nothing to compute")
        return 0

    df = pd.read_parquet(arch)
    datecol = "date" if "date" in df.columns else ("ts" if "ts" in df.columns else None)
    if datecol is None or "symbol" not in df.columns:
        print(f"{arch} has no date/symbol column")
        return 0
    df = df[["symbol", datecol, "close", "volume"]].dropna(subset=["close"])
    df["symbol"] = df["symbol"].astype(str)
    df = df.sort_values(["symbol", datecol])

    counts = df.groupby("symbol").size().sort_values(ascending=False)
    keep = list(counts[counts >= args.min_bars].index)[:args.max_symbols]
    df = df[df["symbol"].isin(keep)]

    out: dict[str, dict] = {}
    for sym, g in df.groupby("symbol", sort=False):
        if len(g) < args.min_bars:
            continue
        c = g["close"].astype(float).reset_index(drop=True)
        r = rsi(c)
        sma = c.rolling(200, min_periods=200).mean()
        above = (c > sma)
        labels = [bucket(r.iloc[i], bool(above.iloc[i])) for i in range(len(c))]
        if not labels or labels[-1] is None:
            continue
        today = labels[-1]

        fwd = {}
        for h in FWD:
            fwd[h] = (c.shift(-h) / c - 1.0) * 100.0

        # every past day in the same bucket, excluding the tail where the future is unknown
        horizon = max(FWD)
        idx = [i for i in range(len(c) - horizon) if labels[i] == today]
        if len(idx) < args.min_cases:
            continue
        rec = {"bucket": today, "n": len(idx)}
        ok = True
        for h in FWD:
            vals = pd.Series([fwd[h].iloc[i] for i in idx]).dropna()
            if len(vals) < args.min_cases:
                ok = False
                break
            rec[f"fwd{h}_median"] = round(float(vals.median()), 2)
            rec[f"fwd{h}_hit"] = round(100.0 * float((vals > 0).mean()), 1)
        if not ok:
            continue
        rec["last"] = round(float(c.iloc[-1]), 2)
        rec["rsi"] = round(float(r.iloc[-1]), 1) if np.isfinite(r.iloc[-1]) else None
        out[sym.replace(".NS", "").replace(".BO", "")] = rec

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": Path(arch).name,
        "count": len(out),
        "min_cases": args.min_cases,
        "horizons": list(FWD),
        "symbols": out,
        "note": ("For each stock, the days in its own history with the same RSI bucket and "
                 "the same side of the 200-day average, and what the next 5 and 20 sessions "
                 "did. A base rate, not a forecast: the past distribution of a stock is not "
                 "a promise about the next month, and a sample under about 30 cases is thin."),
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest} ({dest.stat().st_size / 1e3:.0f} KB) | {len(out)} symbols "
          f"with at least {args.min_cases} cases")
    top = sorted(out.items(), key=lambda kv: -(kv[1]["fwd20_median"] or -999))[:5]
    for sym, rec in top:
        print(f"  {sym:<12} {rec['bucket']:<16} n={rec['n']:<4} "
              f"5d {rec['fwd5_median']:+.2f}% ({rec['fwd5_hit']}%) "
              f"20d {rec['fwd20_median']:+.2f}% ({rec['fwd20_hit']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
