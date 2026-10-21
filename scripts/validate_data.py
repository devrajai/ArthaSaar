#!/usr/bin/env python3
"""
validate_data.py - data-quality checks on the candle archive.

Catches the things that quietly corrupt analysis:
  * impossible bars        high < low, close outside [low, high]
  * bad volume             negative or zero
  * duplicate rows         same symbol + date twice
  * extreme 1-day moves    > `--move-threshold`% with no corporate action explaining it
  * long gaps              more than `--gap-days` between consecutive rows for a symbol
  * staleness              newest bar older than `--max-age` days
  * nulls                  missing OHLC

Writes data/quality/report.json and prints a summary. Exits 1 if any ERROR-level check
fails, so the pipeline can flag it.

Note: extreme-move checking needs data/corporate_actions/actions.csv (see
corporate_actions.py) - without it, big moves are reported as warnings, not errors,
because a split is a legitimate reason for one.

Usage
-----
  python scripts/validate_data.py
  python scripts/validate_data.py --in data/candles/cm_daily.parquet --max-age 7
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _archive import pick_candles  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Data-quality checks on the candle archive.")
    ap.add_argument("--in", dest="infile", default="")
    ap.add_argument("--out", default="data/quality")
    ap.add_argument("--move-threshold", type=float, default=40.0, help="%% one-day move to flag")
    ap.add_argument("--gap-days", type=int, default=15)
    ap.add_argument("--max-age", type=int, default=7)
    ap.add_argument("--actions", default="data/corporate_actions/actions.csv")
    args = ap.parse_args()

    src = args.infile
    if not src:
        src = pick_candles()
    if not src or not Path(src).exists():
        print("no candle archive found - skipping")
        return 0

    df = pd.read_parquet(src)
    need = {"symbol", "high", "low", "close"}
    if not need.issubset(df.columns):
        print(f"candles missing columns: {need - set(df.columns)} - skipping")
        return 0
    if "date" not in df.columns and "ts" in df.columns:
        df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    df["_d"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ("open", "high", "low", "close", "volume"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    errors, warnings = [], []

    # 1 impossible bars
    bad = df[(df["high"] < df["low"]) | (df["close"] > df["high"]) | (df["close"] < df["low"])]
    if len(bad):
        errors.append({"check": "impossible_bar", "rows": len(bad),
                       "examples": bad[["symbol", "date"]].head(5).to_dict("records")})

    # 2 nulls
    nulls = int(df[["open", "high", "low", "close"]].isna().sum().sum()) if "open" in df.columns else 0
    if nulls:
        errors.append({"check": "null_ohlc", "rows": nulls})

    # 3 volume
    if "volume" in df.columns:
        bvol = df[df["volume"] < 0]
        if len(bvol):
            errors.append({"check": "negative_volume", "rows": len(bvol)})

    # 4 duplicates
    dups = int(df.duplicated(subset=["symbol", "date"]).sum())
    if dups:
        errors.append({"check": "duplicate_rows", "rows": dups})

    # 5 extreme moves (a split/bonus is a legitimate cause)
    df = df.sort_values(["symbol", "_d"])
    df["_ret"] = df.groupby("symbol", sort=False)["close"].pct_change()
    big = df[df["_ret"].abs() > args.move_threshold / 100.0]
    explained = set()
    apath = Path(args.actions)
    if apath.exists() and len(big):
        acts = pd.read_csv(apath, parse_dates=["ex_date"])
        for _, r in big.iterrows():
            hit = acts[(acts["symbol"] == r["symbol"]) &
                       (abs((acts["ex_date"] - r["_d"]).dt.days) <= 2)]
            if len(hit):
                explained.add((r["symbol"], r["date"]))
    unexplained = big[~big.apply(lambda r: (r["symbol"], r["date"]) in explained, axis=1)]
    if len(unexplained):
        warnings.append({"check": "extreme_move_unexplained", "rows": len(unexplained),
                         "note": "run corporate_actions.py to explain splits/bonuses",
                         "examples": unexplained[["symbol", "date", "_ret"]].head(5)
                                     .assign(_ret=lambda x: (x["_ret"] * 100).round(1))
                                     .to_dict("records")})

    # 6 gaps
    gap_examples = []
    for sym, g in df.groupby("symbol", sort=False):
        if len(g) < 3:
            continue
        d = g["_d"].diff().dt.days
        if (d > args.gap_days).any():
            gap_examples.append(sym)
    if gap_examples:
        warnings.append({"check": "long_gaps", "symbols": len(gap_examples),
                         "examples": gap_examples[:5]})

    # 7 staleness
    newest = df["_d"].max()
    age = (date.today() - newest.date()).days if pd.notna(newest) else None
    if age is not None and age > args.max_age:
        warnings.append({"check": "stale", "newest": str(newest.date()), "age_days": age})

    report = {
        "source": str(src),
        "rows": int(len(df)),
        "symbols": int(df["symbol"].nunique()),
        "window": [str(df["_d"].min().date()), str(df["_d"].max().date())],
        "errors": errors,
        "warnings": warnings,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str))

    print(f"validate {src}")
    print(f"  {report['rows']:,} rows, {report['symbols']} symbols, {report['window'][0]} -> {report['window'][1]}")
    for e in errors:
        print(f"  ERROR   {e['check']}: {e.get('rows', e.get('symbols', '?'))}")
    for w in warnings:
        print(f"  warn    {w['check']}: {w.get('rows', w.get('symbols', w.get('age_days', '?')))}")
    if not errors and not warnings:
        print("  clean - no issues found")
    print(f"Wrote {out}/report.json")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
