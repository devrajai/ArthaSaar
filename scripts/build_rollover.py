#!/usr/bin/env python3
"""
build_rollover.py - how much of the market's futures book is being carried forward.

WHY THIS EXISTS
Rollover is the one number futures traders ask for every expiry week and no free site
publishes: of the open interest sitting in the expiring contract, how much has already
been rebuilt in the next one. The F&O bhavcopy carries every expiry of every future, so
this is a group-by, not a new data source.

HOW IT IS COMPUTED
  rollover %  = next-month OI / (near-month OI + next-month OI) x 100
  added today = the change in open interest in the NEXT contract on the day
A high rollover with next-month OI rising means positions are being carried. A low one
with both falling means they are being closed instead - the trader is leaving, not rolling.

Input:  data/csv/fo/*.csv  (canonical schema, futures rows)
Output: docs/rollover.json

Usage:
  python scripts/build_rollover.py
  python scripts/build_rollover.py --file data/csv/fo/fo_2026-11-06.csv
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

OUT = "docs/rollover.json"
FUT = ("STF", "IDF")
INDEXES = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50")


def latest(pattern: str) -> str | None:
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def num(v, default=0.0):
    try:
        f = float(v)
        return f if np.isfinite(f) else default
    except Exception:
        return default


def row_for(sym: str, g: pd.DataFrame) -> dict | None:
    g = g.sort_values("expiry")
    exps = list(g["expiry"].astype(str).unique())
    if len(exps) < 2:
        return None
    near = g[g["expiry"].astype(str) == exps[0]].iloc[0]
    nxt = g[g["expiry"].astype(str) == exps[1]].iloc[0]
    near_oi, next_oi = num(near["oi"]), num(nxt["oi"])
    total = near_oi + next_oi
    if total <= 0:
        return None
    spot = num(near["underlying"], 0.0)
    price = num(near["close"], 0.0)
    return {
        "symbol": sym,
        "near_expiry": exps[0],
        "next_expiry": exps[1],
        "near_oi": int(near_oi),
        "next_oi": int(next_oi),
        "rollover_pct": round(100.0 * next_oi / total, 2),
        "near_oi_chg": int(num(near["oi_change"])),
        "next_oi_chg": int(num(nxt["oi_change"])),
        "fut_close": round(price, 2) if price else None,
        "spot": round(spot, 2) if spot else None,
        "basis_pct": round(100.0 * (price - spot) / spot, 2) if (price and spot) else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Futures rollover from the F&O bhavcopy.")
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--min-oi", type=float, default=10000, help="ignore contracts below this OI")
    args = ap.parse_args()

    path = args.file or latest("data/csv/fo/*.csv")
    if not path or not Path(path).exists():
        print("no F&O csv on disk - nothing to publish")
        return 0

    df = pd.read_csv(path, low_memory=False)
    if "instrm_type" not in df.columns:
        print("that file has no instrm_type column - not an F&O file")
        return 0
    fut = df[df["instrm_type"].astype(str).str.upper().isin(FUT)].copy()
    if fut.empty:
        print("no futures rows in that file")
        return 0
    for c in ("oi", "oi_change", "close", "underlying"):
        fut[c] = pd.to_numeric(fut.get(c), errors="coerce")
    fut = fut[fut["expiry"].notna()]

    indices, stocks = {}, []
    for sym, g in fut.groupby("symbol"):
        r = row_for(str(sym), g)
        if not r:
            continue
        if r["near_oi"] + r["next_oi"] < args.min_oi:
            continue
        if str(sym).upper() in INDEXES:
            indices[str(sym).upper()] = r
        else:
            stocks.append(r)

    stocks.sort(key=lambda x: -x["rollover_pct"])
    market_roll = None
    if stocks:
        tot_near = sum(s["near_oi"] for s in stocks)
        tot_next = sum(s["next_oi"] for s in stocks)
        if tot_near + tot_next:
            market_roll = round(100.0 * tot_next / (tot_near + tot_next), 2)

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": str(fut["date"].iloc[0])[:10] if "date" in fut.columns else None,
        "source": Path(path).name,
        "market_rollover_pct": market_roll,
        "count": len(stocks),
        "indices": indices,
        "stocks": stocks[:40],
        "note": ("Rollover is next-month open interest as a share of the two nearest "
                 "contracts. It is a measure of positions being carried, not of direction: "
                 "a high rollover says traders stayed, not that they are bullish."),
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest} ({dest.stat().st_size / 1e3:.0f} KB) | "
          f"{len(stocks)} stocks, market rollover {market_roll}%")
    for k, v in list(indices.items())[:3]:
        print(f"  {k}: near {v['near_expiry']} {v['near_oi']:,} -> next {v['next_expiry']} "
              f"{v['next_oi']:,} = {v['rollover_pct']}% (next added {v['next_oi_chg']:+,})")
    for s in stocks[:3]:
        print(f"  {s['symbol']}: {s['rollover_pct']}% rollover, next added {s['next_oi_chg']:+,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
