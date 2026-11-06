#!/usr/bin/env python3
"""
timesfm_score.py - keep score on the TimesFM forecasts.

WHY THIS EXISTS
The site publishes a 21-session forecast and a walk-forward accuracy table, but that
table is about the six statistical models in scripts/forecast.py - it says nothing
about TimesFM itself. A forecast nobody scores is decoration.

HOW IT SCORES, AND WHY THIS WAY
Every run of timesfm_forecast.py appends what it predicted to data/forecast_log.jsonl.
This script reads that log, waits until the horizon has actually elapsed in the price
archive, and then compares the prediction with the close that followed. Three numbers
come out of that, and they answer three different questions:

  median_abs_error_pct   how wrong the median was, on average (a miss is a miss in
                         either direction)
  band_hit_pct           how often the realised close landed inside the model's own
                         10th-90th percentile band - this is the one that tests whether
                         the uncertainty it reports means anything
  direction_hit_pct      how often the sign was right, which is what most people
                         actually want and the hardest thing to get

A model can be bad at the first, good at the second and coin-flip on the third. Showing
all three stops any one of them flattering the model.

Input:   data/forecast_log.jsonl   (appended by timesfm_forecast.py)
         data/candles/*.parquet    (the price archive)
Output:  docs/timesfm_score.json

Usage:
  python scripts/timesfm_score.py
  python scripts/timesfm_score.py --min-n 5
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

LOG = "data/forecast_log.jsonl"
OUT = "docs/timesfm_score.json"
# The kill switch. If the model's own band stops containing what actually happened, the
# forecast is hidden rather than shown with a disclaimer. Hiding it is a stronger signal
# than any note under a chart, and it fails in the safe direction.
KILL_BAND_HIT = 70.0      # percent of realised closes that must land inside the 10-90 band
KILL_MIN_N = 100          # settled forecasts needed before the switch is allowed to fire

ARCHIVES = ("data/candles/daily_adj.parquet",
            "data/candles/cm_daily_adj.parquet",
            "data/candles/daily.parquet",
            "data/candles/cm_daily.parquet")


def load_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("rows") and e.get("as_of"):
            out.append(e)
    out.sort(key=lambda e: e["as_of"])
    return out


def load_prices() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """symbol -> (dates as int64 yyyymmdd, closes). Only the columns we need."""
    for cand in ARCHIVES:
        p = Path(cand)
        if not p.exists():
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        datecol = "date" if "date" in df.columns else ("ts" if "ts" in df.columns else None)
        if datecol is None or "symbol" not in df.columns or "close" not in df.columns:
            continue
        df = df[[ "symbol", datecol, "close" ]].dropna()
        if df.empty:
            continue
        # normalise to yyyymmdd integers so a string date and a timestamp sort together
        d = pd.to_datetime(df[datecol], errors="coerce")
        df = df.assign(_d=(d.dt.year * 10000 + d.dt.month * 100 + d.dt.day))
        df = df.dropna(subset=["_d"])
        df["_d"] = df["_d"].astype("int64")
        out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for sym, g in df.sort_values("_d").groupby("symbol"):
            key = str(sym).replace(".NS", "").replace(".BO", "")
            out[key] = (g["_d"].to_numpy(), g["close"].astype(float).to_numpy())
        if out:
            return out
    return {}


def as_int(datestr: str) -> int:
    try:
        return int(str(datestr)[:10].replace("-", ""))
    except Exception:
        return 0


def score_one(entry: dict, prices: dict, horizon: int) -> list[dict]:
    """Every symbol in this log entry that the archive can now settle."""
    base_day = as_int(entry.get("as_of"))
    if not base_day:
        return []
    rows = []
    for r in entry["rows"]:
        key = str(r.get("symbol", "")).replace(".NS", "").replace(".BO", "")
        pk = prices.get(key)
        if not pk:
            continue
        dates, closes = pk
        i0 = int(np.searchsorted(dates, base_day, side="left"))
        if i0 >= len(dates):
            continue
        i1 = i0 + horizon
        if i1 >= len(dates):
            continue                       # horizon has not elapsed yet - not scored
        c0, c1 = float(closes[i0]), float(closes[i1])
        if c0 <= 0 or c1 <= 0:
            continue
        realised = (c1 / c0 - 1) * 100
        med = r.get("median_chg_pct")
        lo, hi = r.get("low10_chg_pct"), r.get("high90_chg_pct")
        if med is None:
            continue
        rows.append({
            "symbol": key,
            "as_of": entry["as_of"][:10],
            "settled_on": str(int(dates[i1])),
            "forecast_pct": round(float(med), 2),
            "realised_pct": round(realised, 2),
            "error_pct": round(abs(realised - float(med)), 2),
            "in_band": (lo is not None and hi is not None and
                        float(lo) <= realised <= float(hi)),
            "direction_ok": (realised >= 0) == (float(med) >= 0),
        })
    return rows


def summarise(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    err = [r["error_pct"] for r in rows]
    return {
        "n": len(rows),
        "median_abs_error_pct": round(float(np.median(err)), 2),
        "mean_abs_error_pct": round(float(np.mean(err)), 2),
        "band_hit_pct": round(100 * sum(1 for r in rows if r["in_band"]) / len(rows), 1),
        "direction_hit_pct": round(100 * sum(1 for r in rows if r["direction_ok"]) / len(rows), 1),
        "median_realised_pct": round(float(np.median([r["realised_pct"] for r in rows])), 2),
        "median_forecast_pct": round(float(np.median([r["forecast_pct"] for r in rows])), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Score TimesFM against what actually happened.")
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--min-n", type=int, default=5,
                    help="a run needs this many settled symbols to be reported")
    ap.add_argument("--recent", type=int, default=60)
    args = ap.parse_args()

    log = load_log(args.log)
    prices = load_prices()

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs_logged": len(log),
        "scored": 0,
        "by_run": [],
        "overall": {"n": 0},
        "recent": [],
    }

    if not log:
        payload["note"] = ("No forecast log yet. timesfm_forecast.py appends to "
                           "data/forecast_log.jsonl on every run; scoring starts once one "
                           "horizon has elapsed.")
    elif not prices:
        payload["note"] = ("The price archive was not found, so nothing can be settled. "
                           "Run the candle archive step first.")
    else:
        everything: list[dict] = []
        for e in log:
            h = int(e.get("horizon_days") or 21)
            rows = score_one(e, prices, h)
            if not rows:
                continue
            s = summarise(rows)
            if s["n"] >= args.min_n:
                s["as_of"] = e["as_of"][:10]
                payload["by_run"].append(s)
            everything.extend(rows)
        everything.sort(key=lambda r: (r["as_of"], r["symbol"]), reverse=True)
        payload["recent"] = everything[:args.recent]
        payload["scored"] = len(everything)
        payload["overall"] = summarise(everything)
        if not everything:
            payload["note"] = ("Nothing has settled yet - every logged forecast still has its "
                               "horizon in the future. The first scores appear one horizon "
                               "after the first logged run.")

    o = payload["overall"]
    n = int(o.get("n") or 0)
    if n >= KILL_MIN_N:
        hit = float(o.get("band_hit_pct") or 0)
        payload["status"] = "ok" if hit >= KILL_BAND_HIT else "under_review"
        payload["status_reason"] = (f"band hit {hit}% over {n} settled forecasts "
                                    f"(threshold {KILL_BAND_HIT}%)")
    else:
        payload["status"] = "too_early"
        payload["status_reason"] = (f"only {n} settled forecasts; {KILL_MIN_N} are needed "
                                    f"before this can be judged")

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    o = payload["overall"]
    print(f"status: {payload['status']} - {payload['status_reason']}")
    if o.get("n"):
        print(f"scored {o['n']} forecasts over {len(payload['by_run'])} runs | "
              f"median miss {o['median_abs_error_pct']}% | band hit {o['band_hit_pct']}% | "
              f"direction {o['direction_hit_pct']}%")
    else:
        print(f"nothing settled yet | {len(log)} runs logged")
    print(f"Wrote {dest} ({dest.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
