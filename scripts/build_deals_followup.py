#!/usr/bin/env python3
"""
build_deals_followup.py - what happens after a bulk deal, and who keeps showing up.

WHY THIS EXISTS
docs/deals.json holds one day of NSE bulk and block deals and forgets it. Two useful things
are impossible from one day: whether a bulk buy is followed by anything, and whether the
same client is quietly accumulating across several days. So this keeps the deals it sees in
data/deals_history.json and, once a deal is old enough to have a future, measures it.

WHAT IT PUBLISHES
  today     per symbol, the net value bought or sold, and any client appearing more than once
  follow_up the median 5- and 20-session move after a bulk or block deal, split by buy and
            sell, with the number of cases that have actually aged that far

It reports nothing about follow-through until deals have aged. A base rate built on deals
from last week is not a base rate.

Input:  docs/deals.json          (today's deals)
        data/deals_history.json  (kept by this script)
        the candle archive       (to measure what happened next)
Output: data/deals_history.json  +  docs/deals_followup.json

Usage:
  python scripts/build_deals_followup.py
  python scripts/build_deals_followup.py --keep-days 400
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

DEALS = "docs/deals.json"
HIST = "data/deals_history.json"
OUT = "docs/deals_followup.json"
ARCHIVES = ("data/candles/daily_adj.parquet", "data/candles/cm_daily_adj.parquet",
            "data/candles/daily.parquet", "data/candles/cm_daily.parquet")
HORIZONS = (5, 20)


def iso(d: str) -> str | None:
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(d).strip(), fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None


def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk/block deal follow-through.")
    ap.add_argument("--keep-days", type=int, default=400)
    ap.add_argument("--min-cases", type=int, default=20)
    args = ap.parse_args()

    d = load(DEALS)
    if not d:
        print("no docs/deals.json - nothing to record")
        return 0

    # ---- normalise today's deals and merge into the history ----
    hist = load(HIST) or {"deals": []}
    seen = {(x["date"], x["symbol"], x["client"], x["side"], x["qty"]) for x in hist.get("deals", [])}
    added = 0
    for kind in ("bulk", "block"):
        for r in d.get(kind) or []:
            if len(r) < 6:
                continue
            date = iso(r[0])
            if not date:
                continue
            try:
                qty = float(r[4])
                price = float(r[5])
            except Exception:
                continue
            key = (date, str(r[1]), str(r[2]), str(r[3]).upper(), qty)
            if key in seen:
                continue
            seen.add(key)
            hist["deals"].append({"date": date, "symbol": str(r[1]), "client": str(r[2]),
                                  "side": str(r[3]).upper(), "qty": qty, "price": price,
                                  "value": round(qty * price, 2), "kind": kind})
            added += 1

    cutoff = (datetime.now() - pd.Timedelta(days=args.keep_days)).strftime("%Y-%m-%d")
    hist["deals"] = [x for x in hist["deals"] if x["date"] >= cutoff]
    dest_hist = Path(HIST)
    dest_hist.parent.mkdir(parents=True, exist_ok=True)
    dest_hist.write_text(json.dumps(hist, separators=(",", ":")))
    print(f"deals history: +{added} new, {len(hist['deals'])} stored")

    today = max((x["date"] for x in hist["deals"]), default=None)
    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": today,
        "stored": len(hist["deals"]),
        "today": {"symbols": [], "repeat_clients": []},
        "follow_up": {},
        "note": ("A bulk or block deal is a completed transaction, not an opinion: it says "
                 "someone moved size, not that they will be right. The follow-through is the "
                 "median move after past deals of the same kind, and it is a base rate."),
    }

    # ---- today: net value per symbol, and clients appearing more than once ----
    if today:
        todays = [x for x in hist["deals"] if x["date"] == today]
        net: dict[str, float] = {}
        for x in todays:
            sign = 1.0 if x["side"].startswith("B") else -1.0
            net[x["symbol"]] = net.get(x["symbol"], 0.0) + sign * x["value"]
        rows = sorted(({"symbol": s, "net_cr": round(v / 1e7, 2)} for s, v in net.items()),
                      key=lambda r: -abs(r["net_cr"]))
        payload["today"]["symbols"] = rows[:20]

        by_client: dict[str, list] = {}
        for x in todays:
            by_client.setdefault(x["client"], []).append(x)
        rep = []
        for client, xs in by_client.items():
            if len(xs) < 2:
                continue
            rep.append({"client": client, "deals": len(xs),
                        "symbols": sorted({x["symbol"] for x in xs})[:6],
                        "value_cr": round(sum(x["value"] for x in xs) / 1e7, 2)})
        rep.sort(key=lambda r: -r["value_cr"])
        payload["today"]["repeat_clients"] = rep[:10]

    # ---- follow-through, only for deals old enough to have a future ----
    arch = next((p for p in ARCHIVES if Path(p).exists()), None)
    if arch and hist["deals"]:
        df = pd.read_parquet(arch)
        datecol = "date" if "date" in df.columns else ("ts" if "ts" in df.columns else None)
        if datecol and {"symbol", "close"}.issubset(df.columns):
            df = df[["symbol", datecol, "close"]].dropna()
            df["symbol"] = df["symbol"].astype(str).str.replace(r"\.(NS|BO)$", "", regex=True)
            df["_d"] = pd.to_datetime(df[datecol], errors="coerce").dt.strftime("%Y-%m-%d")
            df = df.dropna(subset=["_d"]).sort_values("_d")
            prices = {s: (g["_d"].to_numpy(), g["close"].astype(float).to_numpy())
                      for s, g in df.groupby("symbol")}

            for h in HORIZONS:
                for side in ("BUY", "SELL"):
                    moves = []
                    for x in hist["deals"]:
                        if not x["side"].startswith(side[0]):
                            continue
                        pk = prices.get(x["symbol"])
                        if not pk:
                            continue
                        dates, closes = pk
                        i0 = int(np.searchsorted(dates, x["date"], side="left"))
                        i1 = i0 + h
                        if i0 >= len(dates) or i1 >= len(dates):
                            continue
                        c0, c1 = closes[i0], closes[i1]
                        if c0 > 0 and c1 > 0:
                            moves.append((c1 / c0 - 1.0) * 100.0)
                    if len(moves) >= args.min_cases:
                        s = pd.Series(moves)
                        payload["follow_up"][f"{side.lower()}_{h}d"] = {
                            "n": int(len(moves)),
                            "median_pct": round(float(s.median()), 2),
                            "hit_pct": round(100.0 * float((s > 0).mean()), 1),
                        }

    dest = Path(OUT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest} | {len(payload['today']['symbols'])} symbols today, "
          f"{len(payload['today']['repeat_clients'])} repeat clients, "
          f"{len(payload['follow_up'])} follow-through buckets with enough cases")
    if not payload["follow_up"]:
        print("  no follow-through yet - deals need to age past the horizon, and the card "
              "says so rather than showing a number built on three rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
