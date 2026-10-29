#!/usr/bin/env python3
"""Option writing walls - where the big OI sits, and whether its movement means anything.

WHAT THIS IS, AND WHAT IT IS NOT
The guide this came from is an INTRADAY indicator: 1-minute and 3-minute charts with option
writing tracked live through the session. That cannot be built from free data. Our F&O
source is the end-of-day bhavcopy - one snapshot per day - and Yahoo, which the Worker
proxies, serves intraday PRICE but no option chain at all. NSE's live chain endpoint is
rate-limited and blocked from outside India. Live strike-level OI is a paid feed.

So this is the DAILY version of the same idea, and it is labelled as such everywhere. It
shows where the walls stood at yesterday's close and whether they moved. It is not a
scalping tool and must not be used as one.

THE CLAIM BEING TESTED
The guide says: red (put) walls stepping UP = bullish, blue (call) walls stepping DOWN =
bearish. That is a testable statement, so it is tested rather than repeated - forward
returns after each kind of shift, against the index's own average move over the same
horizon. If the edge is small relative to the spread, it is not tradable after costs, and
this says so.
"""
import json, os, sys
from datetime import datetime, timezone

SRC = "data/oi/oi_history.parquet"
LADDER = "docs/oi_strikes.json"
OUT = "docs/oi_walls.json"
INDICES = ("NIFTY", "BANKNIFTY")
HORIZONS = (1, 5, 20)
MIN_CASES = 20


def pct(a, b):
    return (a / b - 1.0) * 100.0 if b else None


def main():
    import pandas as pd

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "ladder": {}, "wall_shifts": {}, "note": ""}

    if not os.path.exists(SRC):
        out["note"] = "No option-chain history on disk yet."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("oi walls: skipped (no history)")
        return 0

    df = pd.read_parquet(SRC)
    print("  %d rows, %s -> %s" % (len(df), df["date"].min(), df["date"].max()))

    # real closes, so forward returns are on the index itself
    fallback = {}
    if "spot" in df.columns and "spot_source" in df.columns:
        for r in df[df["spot_source"] == "underlying"].itertuples(index=False):
            d = str(getattr(r, "date"))[:10]
            v = getattr(r, "spot")
            if v == v and v:
                fallback.setdefault(getattr(r, "index"), {})[d] = float(v)
    yahoo = {}
    for path, key in (("data/yahoo/NSEI.parquet", "NIFTY"),
                      ("data/yahoo/NSEBANK.parquet", "BANKNIFTY")):
        if not os.path.exists(path):
            continue
        try:
            y = pd.read_parquet(path)
            dcol = next((c for c in ("date", "Date") if c in y.columns), None)
            ccol = next((c for c in ("close", "Close") if c in y.columns), None)
            if dcol and ccol:
                yahoo[key] = {str(d)[:10]: float(c) for d, c in zip(y[dcol], y[ccol])
                              if c == c and c and c > 0}
        except Exception:
            pass

    total = 0
    for idx in INDICES:
        g = df[df["index"] == idx].sort_values("date")
        cl = yahoo.get(idx) or fallback.get(idx) or {}
        rows = []
        for r in g.itertuples(index=False):
            d = str(getattr(r, "date"))[:10]
            rows.append({"date": d,
                         "close": cl.get(d),
                         "call_wall": getattr(r, "call_wall", None),
                         "put_wall": getattr(r, "put_wall", None)})
        for i, x in enumerate(rows):
            for h in HORIZONS:
                j = i + h
                x["fwd%d" % h] = (pct(rows[j]["close"], x["close"])
                                  if j < len(rows) and x["close"] and rows[j]["close"] else None)

        # today's ladder, from the strike-wise file
        try:
            lad = json.load(open(LADDER))
            if lad.get("indices") and idx in lad["indices"]:
                out["ladder"][idx] = lad["indices"][idx]
        except Exception:
            pass

        # ---- wall shifts ----
        call_down, put_up, call_up, put_down = [], [], [], []
        for i in range(1, len(rows)):
            prev, cur = rows[i - 1], rows[i]
            if prev["call_wall"] and cur["call_wall"]:
                if cur["call_wall"] < prev["call_wall"]:
                    call_down.append(cur)
                elif cur["call_wall"] > prev["call_wall"]:
                    call_up.append(cur)
            if prev["put_wall"] and cur["put_wall"]:
                if cur["put_wall"] > prev["put_wall"]:
                    put_up.append(cur)
                elif cur["put_wall"] < prev["put_wall"]:
                    put_down.append(cur)

        def avg(subset, h):
            v = [x["fwd%d" % h] for x in subset if x["fwd%d" % h] is not None]
            return (round(sum(v) / len(v), 3), len(v)) if len(v) >= MIN_CASES else (None, len(v))

        base = {str(h): avg(rows, h) for h in HORIZONS}
        out["wall_shifts"][idx] = {
            "baseline": base,
            "days": len(rows),
            "call_wall_down": {"n": len(call_down),
                               **{str(h): avg(call_down, h) for h in HORIZONS}},
            "call_wall_up": {"n": len(call_up),
                             **{str(h): avg(call_up, h) for h in HORIZONS}},
            "put_wall_up": {"n": len(put_up),
                            **{str(h): avg(put_up, h) for h in HORIZONS}},
            "put_wall_down": {"n": len(put_down),
                              **{str(h): avg(put_down, h) for h in HORIZONS}},
        }
        total += 1

    out["count"] = total
    out["min_cases"] = MIN_CASES
    out["note"] = ("Daily option-writing walls at the previous close, and whether their "
                   "movement precedes anything. END-OF-DAY ONLY - this is not the live "
                   "intraday indicator from the original guide, which needs a paid OI feed.")
    out["cautions"] = {
        "eod": "One snapshot per day. Intraday wall movement is not available free.",
        "all_expiries": "Open interest is summed across expiries, so the wall is not the nearest-expiry chain.",
        "not_a_signal": "A historical tendency is not a prediction, and not a recommendation.",
        "small": "Buckets under %d cases are withheld." % MIN_CASES,
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))

    for idx, s in out["wall_shifts"].items():
        print("   %s (%d days)" % (idx, s["days"]))
        print("      baseline       1d %s  5d %s  20d %s" % (s["baseline"]["1"], s["baseline"]["5"], s["baseline"]["20"]))
        for k in ("call_wall_down", "put_wall_up", "call_wall_up", "put_wall_down"):
            v = s[k]
            print("      %-14s n=%-4d 1d %s  5d %s  20d %s" % (k, v["n"], v["1"], v["5"], v["20"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
