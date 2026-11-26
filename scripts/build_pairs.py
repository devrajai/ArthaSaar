#!/usr/bin/env python3
"""
build_pairs.py - live z-scores for the elite pair list, computed from our own closes.

Why this exists
---------------
A daily pair tracker was writing to a Google Sheet, but every z-score it wrote was identical to
the previous run's - BAJFINANCE/CHOLAFIN read 1.0877 on two different dates, and so did every
other pair. A new date with old numbers is worse than no update, because it looks like a check.

This computes the spread from docs/series.json, which the pipeline rebuilds every night from the
NSE bhavcopy. If the closes move, the z-score moves. If a leg is missing, the pair says so
instead of carrying a stale number forward.

The method
----------
For a pair (A, B): spread = ln(price_A) - ln(price_B). The z-score is how far today's spread sits
from its own mean over the lookback window, in standard deviations. Ratio rather than difference,
because a spread between two differently-priced stocks is not comparable in rupees.

Honest limits
-------------
  * A z-score is not a signal. It says the ratio is unusual against its own recent past; it does
    not say it will revert, and a broken pair can stay at 3 sigma for months.
  * Cointegration is not tested here. The pair list came from the user's own analysis; this only
    measures where the spread is now.
  * Closes are adjusted for splits and bonuses upstream. An unadjusted split would fake a 2-sigma
    move overnight.

Usage
-----
  python scripts/build_pairs.py
  python scripts/build_pairs.py --window 60 --entry 2.0

Output: docs/pairs.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/pairs.json"
SERIES = "docs/series.json"

# The 21 pairs from the user's pair-trading workbook. A/B: A is the long leg on a negative
# z-score, B the short leg.
PAIRS = [
    ("BAJFINANCE", "CHOLAFIN"), ("CGPOWER", "DATAPATTNS"), ("ATHERENERG", "SONACOMS"),
    ("PERSISTENT", "SAGILITY"), ("CANBK", "SBILIFE"), ("ASTRAL", "SUPREMEIND"),
    ("IRFC", "MUTHOOTFIN"), ("IEX", "MUTHOOTFIN"), ("MPHASIS", "SAGILITY"),
    ("CANBK", "HDFCLIFE"), ("KFINTECH", "SBICARD"), ("DATAPATTNS", "POWERINDIA"),
    ("INDUSINDBK", "MANAPPURAM"), ("NATIONALUM", "TATASTEEL"), ("HDFCBANK", "HDFCLIFE"),
    ("HINDALCO", "VEDL"), ("FEDERALBNK", "RBLBANK"), ("INFY", "WIPRO"),
    ("CANBK", "HDFCBANK"), ("JIOFIN", "KFINTECH"), ("DATAPATTNS", "SIEMENS"),
]


def find(series: dict, sym: str):
    """series.json keys are 'SYMBOL.NS'. Accept either form."""
    if sym in series:
        return series[sym]
    for k in (sym + ".NS", sym + ".BO"):
        if k in series:
            return series[k]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--window", type=int, default=60, help="lookback sessions for the mean and sd")
    ap.add_argument("--entry", type=float, default=2.0, help="|z| at which a spread is called")
    ap.add_argument("--watch", type=float, default=1.5)
    args = ap.parse_args()

    try:
        d = json.loads(Path(SERIES).read_text())
        series = d.get("series") or {}
    except Exception as e:
        print(f"series.json unreadable ({type(e).__name__}) - skipping")
        return 0
    if not series:
        print("series.json is empty - skipping")
        return 0

    rows, missing = [], []
    for a, b in PAIRS:
        sa, sb = find(series, a), find(series, b)
        if not sa or not sb:
            missing.append(f"{a}/{b}")
            continue
        # align on the shorter series, both are oldest-first closes
        n = min(len(sa), len(sb))
        if n < 25:
            missing.append(f"{a}/{b}")
            continue
        sa, sb = sa[-n:], sb[-n:]
        spread = []
        for x, y in zip(sa, sb):
            try:
                if x and y and x > 0 and y > 0:
                    spread.append(math.log(x) - math.log(y))
            except Exception:
                continue
        if len(spread) < 25:
            missing.append(f"{a}/{b}")
            continue

        win = spread[-min(args.window, len(spread)):]
        mean = sum(win) / len(win)
        var = sum((v - mean) ** 2 for v in win) / max(1, len(win) - 1)
        sd = math.sqrt(var)
        cur = spread[-1]
        z = (cur - mean) / sd if sd > 1e-12 else None

        if z is None:
            state = "NO SIGNAL"
        elif z <= -args.entry:
            state = "BUY A / SELL B"
        elif z >= args.entry:
            state = "SELL A / BUY B"
        elif abs(z) >= args.watch:
            state = "WATCH"
        else:
            state = "NO SIGNAL"

        rows.append({
            "pair": f"{a}/{b}", "a": a, "b": b,
            "z": None if z is None else round(z, 4),
            "state": state,
            "ratio": round(math.exp(cur), 4),
            "mean_ratio": round(math.exp(mean), 4),
            "sessions": len(spread),
            "a_close": round(sa[-1], 2), "b_close": round(sb[-1], 2),
            "a_chg": round((sa[-1] / sa[-2] - 1) * 100, 2) if len(sa) > 1 and sa[-2] else None,
            "b_chg": round((sb[-1] / sb[-2] - 1) * 100, 2) if len(sb) > 1 and sb[-2] else None,
        })

    rows.sort(key=lambda r: -abs(r["z"] or 0))

    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(rows),
        "window": args.window,
        "entry": args.entry,
        "watch": args.watch,
        "counts": counts,
        "note": ("z-score of the log price ratio against its own mean over the lookback window, "
                 "computed from docs/series.json - the same closes the rest of the site uses. A "
                 "z-score is not a signal: it says the ratio is unusual against its own recent "
                 "past, not that it will revert. Cointegration is not tested. The pair list comes "
                 "from the user's own workbook; this only measures where the spread is now."),
        "missing": missing,
        "pairs": rows,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(rows)} pairs "
          f"| {len(missing)} skipped")
    for r in rows[:5]:
        print(f"   {r['pair']:26s} z={r['z']:>7}  {r['state']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
