#!/usr/bin/env python3
"""
build_vrp.py - is the option market charging more than the market actually moves?

WHY THIS EXISTS
India VIX is the implied 30-day volatility of the Nifty. Realised volatility can be measured
from the index's own closes. The difference between them is the variance risk premium, and
it is the number professional option sellers live on: when implied runs above realised, the
seller is being paid for taking the risk; when it runs below, the buyer is.

  implied 30-day move %  = VIX x sqrt(30/365)
  realised 30-day move % = annualised realised vol of the last 30 sessions x sqrt(30/365)
  premium                = implied - realised, in percentage points

Both are stated as the move over 30 days, so the two numbers mean the same thing to a
reader. The premium is not a signal: it can stay positive for years, and selling volatility
loses money in exactly the tails this number ignores.

Input:  docs/vix.json          (the implied side, already published)
        Nifty daily closes    (data/yahoo/*NSEI*.parquet, else fetched from Yahoo)
Output: docs/vrp.json

Usage:
  python scripts/build_vrp.py
  python scripts/build_vrp.py --window 30 --out docs/vrp.json
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

VIX = "docs/vix.json"
OUT = "docs/vrp.json"
TRADING_DAYS = 252


def nifty_closes() -> pd.Series | None:
    """Daily Nifty closes, from the local Yahoo cache or a fresh download."""
    for p in sorted(glob.glob("data/yahoo/*NSEI*.parquet")) + sorted(glob.glob("data/yahoo/*NSEI*.csv")):
        try:
            df = pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(p)
        except Exception:
            continue
        cols = {c.lower(): c for c in df.columns}
        datecol = cols.get("date") or cols.get("index")
        closecol = cols.get("close")
        if not datecol or not closecol:
            continue
        s = pd.Series(df[closecol].astype(float).values,
                      index=pd.to_datetime(df[datecol], errors="coerce")).dropna()
        if len(s) > 60:
            print(f"  nifty closes: {len(s)} sessions from {p}")
            return s.sort_index()
    try:
        import yfinance as yf
        d = yf.download("^NSEI", period="3y", interval="1d", progress=False, auto_adjust=True)
        if d is None or len(d) < 60:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        s = d["Close"].dropna()
        print(f"  nifty closes: {len(s)} sessions from Yahoo")
        return s
    except Exception as e:
        print(f"  could not get Nifty closes ({type(e).__name__})")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Variance risk premium: implied vs realised.")
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    try:
        vix = json.loads(Path(VIX).read_text())
    except Exception:
        print("no docs/vix.json - nothing to compare against")
        return 0
    series = vix.get("series") or []
    if len(series) < 40:
        print("the VIX series is too short to work with")
        return 0

    closes = nifty_closes()
    if closes is None or len(closes) < args.window + 10:
        print("no Nifty closes available - publishing nothing rather than half the comparison")
        return 0

    imp = pd.Series({pd.Timestamp(d): float(v) for d, v in series if v is not None}).sort_index()
    ret = np.log(closes / closes.shift(1)).dropna()
    # annualised realised vol of the trailing window, then scaled to the same horizon as VIX
    rv_ann = ret.rolling(args.window).std() * math.sqrt(TRADING_DAYS) * 100.0
    scale = math.sqrt(args.window / 365.0)
    real = rv_ann * scale
    implied = imp * scale

    idx = implied.index.intersection(real.index)
    if len(idx) < 30:
        print(f"only {len(idx)} overlapping sessions between VIX and the index - too few")
        return 0

    imp_a, real_a = implied.loc[idx], real.loc[idx]
    prem = (imp_a - real_a).dropna()
    if prem.empty:
        print("no overlapping window to compute a premium")
        return 0

    last = prem.index[-1]
    year = prem[prem.index >= (last - pd.Timedelta(days=365))]
    hist = [{"d": d.strftime("%Y-%m-%d"),
             "imp": round(float(imp_a.loc[d]), 2),
             "real": round(float(real_a.loc[d]), 2),
             "prem": round(float(prem.loc[d]), 2)}
            for d in prem.index[-250:]]

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": last.strftime("%Y-%m-%d"),
        "window": args.window,
        "implied_pct": round(float(imp_a.loc[last]), 2),
        "realised_pct": round(float(real_a.loc[last]), 2),
        "premium_pct": round(float(prem.loc[last]), 2),
        "premium_avg_1y": round(float(year.mean()), 2),
        "paid_pct_1y": round(100.0 * float((year > 0).mean()), 1),
        "n_days_1y": int(len(year)),
        "history": hist,
        "note": ("Implied is India VIX scaled to a 30-day move; realised is the annualised "
                 "volatility of the last 30 Nifty sessions scaled the same way. A positive "
                 "premium means options are priced above what the index actually delivered. "
                 "It is not a signal: the premium has stayed positive for long stretches, and "
                 "selling volatility loses everything in the tail this number ignores."),
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest} | {last.date()}: implied {payload['implied_pct']}% "
          f"vs realised {payload['realised_pct']}% = premium {payload['premium_pct']} pts | "
          f"1y average {payload['premium_avg_1y']} pts, positive on {payload['paid_pct_1y']}% of days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
