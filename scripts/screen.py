#!/usr/bin/env python3
"""
screen.py - run named rules over the indicator snapshot.

Reads data/indicators/latest.parquet (build it with build_indicators.py) and prints the
symbols matching a rule. Rules are transparent one-liners - no black box.

Usage
-----
  python scripts/screen.py --list
  python scripts/screen.py --rule oversold
  python scripts/screen.py --rule trend_up --limit 20
  python scripts/screen.py --rule breakout --symbols RELIANCE TCS
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

# name -> (human description, predicate over the snapshot frame)
RULES = {
    "oversold":      ("RSI(14) < 30", lambda d: d["rsi_14"] < 30),
    "overbought":    ("RSI(14) > 70", lambda d: d["rsi_14"] > 70),
    "trend_up":      ("close > SMA50 > SMA200", lambda d: (d["close"] > d["sma_50"]) & (d["sma_50"] > d["sma_200"])),
    "trend_down":    ("close < SMA50 < SMA200", lambda d: (d["close"] < d["sma_50"]) & (d["sma_50"] < d["sma_200"])),
    "golden_cross":  ("close > SMA200 but SMA50 just below (turn candidate)",
                      lambda d: (d["close"] > d["sma_200"]) & (d["sma_50"] < d["sma_200"])),
    "breakout":      ("close within 1% of the 20-day high", lambda d: d["close"] >= d["dc_upper"] * 0.99),
    "bollinger_squeeze": ("band width in the lowest decile (coiling)",
                          lambda d: d["bb_bandwidth"] <= d["bb_bandwidth"].quantile(0.10)),
    "high_vol":      ("ATR > 4% of price", lambda d: d["atr_pct"] > 0.04),
    "strong_trend":  ("ADX > 25 and +DI > -DI", lambda d: (d["adx"] > 25) & (d["plus_di"] > d["minus_di"])),
    "supertrend_buy":("supertrend flipped long", lambda d: d["st_dir"] > 0),
    "obv_rising":    ("OBV above its own 20-day average proxy (close>sma20 and obv>0)",
                      lambda d: (d["close"] > d["sma_20"]) & (d["obv"] > 0)),
    "pullback":      ("uptrend with RSI cooling below 45",
                      lambda d: (d["close"] > d["sma_200"]) & (d["rsi_14"] < 45)),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Screen the indicator snapshot.")
    ap.add_argument("--in", dest="infile", default="data/indicators/latest.parquet")
    ap.add_argument("--rule", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", default="data/screens")
    args = ap.parse_args()

    if args.list or not args.rule:
        print("rules:")
        for k, (desc, _) in RULES.items():
            print(f"  {k:20s} {desc}")
        return 0

    if args.rule not in RULES:
        raise SystemExit(f"unknown rule '{args.rule}' - try --list")
    desc, fn = RULES[args.rule]

    p = Path(args.infile)
    if not p.exists():
        print(f"no indicator snapshot at {p} - run build_indicators.py first")
        return 0
    df = pd.read_parquet(p)
    if args.symbols:
        df = df[df["symbol"].isin(args.symbols)]

    try:
        mask = fn(df).fillna(False)
    except KeyError as e:
        raise SystemExit(f"rule '{args.rule}' needs column {e} - rebuild indicators") from e

    hits = df[mask]
    print(f"rule: {args.rule}  ({desc})")
    print(f"  {len(hits)} of {len(df)} symbols match")

    cols = [c for c in ["symbol", "date", "close", "rsi_14", "sma_50", "sma_200",
                        "adx", "atr_pct", "bb_bandwidth", "st_dir"] if c in hits.columns]
    if len(hits):
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        hits[cols].to_csv(out / f"{args.rule}.csv", index=False)
        print(hits[cols].head(args.limit).to_string(index=False))
        print(f"\nWrote {out}/{args.rule}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
