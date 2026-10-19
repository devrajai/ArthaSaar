#!/usr/bin/env python3
"""
relative_strength.py - rank symbols by performance against a benchmark.

Relative strength answers "what is leading?" rather than "is it going up?". A stock up
5% while the index is up 12% is weak, not strong.

Computes each symbol's return over N days minus the benchmark's, and a ratio line
(symbol / benchmark) that rises when the symbol outperforms.

Usage
-----
  python scripts/relative_strength.py --benchmark NIFTY50
  python scripts/relative_strength.py --periods 5 20 60 --limit 30
  python scripts/relative_strength.py --benchmark ^NSEI --in data/candles/daily.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Relative strength vs a benchmark.")
    ap.add_argument("--in", dest="infile", default="")
    ap.add_argument("--benchmark", default="NIFTY50", help="a symbol present in the archive")
    ap.add_argument("--periods", nargs="*", type=int, default=[5, 20, 60])
    ap.add_argument("--min-history", type=int, default=80)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--out", default="data/rs")
    args = ap.parse_args()

    src = args.infile
    if not src:
        for cand in ("data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
            if Path(cand).exists():
                src = cand
                break
    if not src or not Path(src).exists():
        print("no candle archive found - skipping")
        return 0

    df = pd.read_parquet(src)
    sortcol = "date" if "date" in df.columns else "ts"
    if args.benchmark not in set(df["symbol"].unique()):
        # fall back to an equal-weight "market" of everything, so the script still works
        bench = (df.groupby(sortcol)["close"].mean().rename("close").reset_index()
                 .assign(symbol="__MARKET__"))
        print(f"benchmark '{args.benchmark}' not in the archive - using an equal-weight market instead")
        bname = "__MARKET__"
    else:
        bench = df[df["symbol"] == args.benchmark][[sortcol, "close"]].copy()
        bench["symbol"] = args.benchmark
        bname = args.benchmark

    bench = bench.sort_values(sortcol)
    bret = {p: bench["close"].iloc[-1] / bench["close"].iloc[-1 - p] - 1
            for p in args.periods if len(bench) > p}

    rows = []
    for sym, g in df.groupby("symbol", sort=False):
        if sym == bname or len(g) < args.min_history:
            continue
        g = g.sort_values(sortcol)
        row = {"symbol": sym, "close": float(g["close"].iloc[-1])}
        for p in args.periods:
            if len(g) > p and p in bret:
                r = g["close"].iloc[-1] / g["close"].iloc[-1 - p] - 1
                row[f"ret_{p}d"] = round(float(r) * 100, 2)
                row[f"rs_{p}d"] = round(float(r - bret[p]) * 100, 2)
        rows.append(row)

    if not rows:
        print("nothing to rank")
        return 0
    res = pd.DataFrame(rows)
    rs_cols = [f"rs_{p}d" for p in args.periods if f"rs_{p}d" in res.columns]
    if rs_cols:
        res["rs_score"] = res[rs_cols].mean(axis=1)
        res = res.sort_values("rs_score", ascending=False)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "latest.csv", index=False)

    print(f"relative strength vs {bname}  |  benchmark returns: "
          + ", ".join(f"{p}d {bret[p] * 100:+.1f}%" for p in sorted(bret)))
    show = ["symbol", "close"] + [c for c in res.columns if c.startswith("rs_")]
    print("\nleaders:")
    print(res[show].head(min(args.limit, 10)).to_string(index=False))
    print("\nlaggards:")
    print(res[show].tail(min(args.limit, 10)).to_string(index=False))
    print(f"\nWrote {out}/latest.csv  ({len(res)} symbols)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
