#!/usr/bin/env python3
"""
build_rank_momentum.py - which stocks are climbing the screener, not just the price.

WHY THIS EXISTS
The screener ranks 2,200 stocks on today's readings and forgets yesterday's. A stock that
moved from rank 340 to 88 on quality measures is a different animal from one that jumped
because of a single gap - and only the second one shows up in a price-mover list. This
keeps one rank snapshot a day and reports who is climbing.

THE COMPOSITE
Three things the screener already computes, each turned into a 0-100 percentile across the
universe that day, then weighted:

    score = 0.40 x percentile(rsi)            momentum of the last two weeks
          + 0.30 x percentile(from_52w_high)  how close to the high (less negative wins)
          + 0.30 x percentile(chg_20d)        the month's move

Percentiles rather than raw values, so the score is comparable across days even when the
whole market moves. That is what makes a rank change meaningful.

Input:  docs/screener.json                  (today)
        data/rank_history.json              (kept by this script, last N days)
Output: data/rank_history.json  +  docs/rank_momentum.json

Usage:
  python scripts/build_rank_momentum.py
  python scripts/build_rank_momentum.py --days 30 --top 20
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCREENER = "docs/screener.json"
HIST = "data/rank_history.json"
OUT = "docs/rank_momentum.json"


def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def composite(rows: list[dict]) -> dict[str, int]:
    """Rank every stock 1..N on a weighted percentile of three published measures."""
    df = pd.DataFrame(rows)
    if df.empty or "symbol" not in df.columns:
        return {}
    # index by symbol, not by row number - ranking the row index published numbers
    # where stock names should have been
    df = df.dropna(subset=["symbol"]).drop_duplicates(subset=["symbol"]).set_index("symbol")
    for c in ("rsi", "from_52w_high", "chg_20d"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    parts, weights = [], {"rsi": 0.40, "from_52w_high": 0.30, "chg_20d": 0.30}
    score = pd.Series(0.0, index=df.index)
    used = 0.0
    for c, w in weights.items():
        col = df[c]
        if col.notna().sum() < 50:
            continue          # not enough data that day - drop the term, do not guess
        pct = col.rank(pct=True) * 100.0
        pct = pct.fillna(50.0)
        score = score + pct * w
        used += w
    if used == 0:
        return {}
    score = score / used
    order = score.sort_values(ascending=False)
    return {str(sym): int(i + 1) for i, sym in enumerate(order.index)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Screener rank momentum.")
    ap.add_argument("--days", type=int, default=30, help="snapshots to keep")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min-days", type=int, default=5,
                    help="days of history before movers are reported")
    args = ap.parse_args()

    sc = load(SCREENER)
    if not sc or not sc.get("rows"):
        print("no screener rows - nothing to rank")
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ranks = composite(sc["rows"])
    if not ranks:
        print("could not build a composite score - no usable columns")
        return 0

    hist = load(HIST) or {"days": []}
    days = [d for d in hist.get("days", []) if d.get("date") != today]
    days.append({"date": today, "ranks": ranks})
    days = sorted(days, key=lambda d: d["date"])[-args.days:]

    dest_hist = Path(HIST)
    dest_hist.parent.mkdir(parents=True, exist_ok=True)
    dest_hist.write_text(json.dumps({"days": days}, separators=(",", ":")))

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": today,
        "universe": len(ranks),
        "days_of_history": len(days),
        "climbers": [],
        "fallers": [],
        "note": ("The composite is a weighted percentile of RSI, distance from the 52-week "
                 "high and the 20-day move, ranked across the whole universe each day. A "
                 "climb means the stock improved relative to every other stock, not that it "
                 "rose - the whole market can fall and a stock still climb this table."),
    }

    if len(days) >= args.min_days:
        base = days[0]["ranks"]
        movers = []
        for sym, r in ranks.items():
            b = base.get(sym)
            if b is None:
                continue
            movers.append((sym, b, r, b - r))          # positive = climbed
        movers.sort(key=lambda x: -x[3])
        def pack(m):
            return {"symbol": m[0], "was": m[1], "now": m[2], "moved": m[3]}
        payload["climbers"] = [pack(m) for m in movers[:args.top] if m[3] > 0]
        payload["fallers"] = [pack(m) for m in movers[-args.top:][::-1] if m[3] < 0]
        payload["compared_with"] = days[0]["date"]

    dest = Path(OUT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest} | {len(ranks)} ranked, {len(days)} day(s) of history")
    if payload["climbers"]:
        print(f"  climbers vs {payload['compared_with']}: " +
              ", ".join(f"{c['symbol']} {c['was']}->{c['now']}" for c in payload["climbers"][:3]))
    else:
        need = args.min_days
        print(f"  no movers yet - history starts today and needs {need} days to be worth "
              f"reporting; the card says so instead of showing noise")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
