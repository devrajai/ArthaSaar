#!/usr/bin/env python3
"""Gann eighths and Fibonacci retracements, with the rate at which each was actually held.

WHY THIS EXISTS
"Give me Gann and Fibonacci levels" is a reasonable request and a testable one. What is not
reasonable is drawing a line on a chart and calling it support because a book said so. Every
level here is published with the number of times price reached it and how often that touch was
followed by a BOUNCE rather than a BREAK.

A NOTE ON A BUG THIS FILE ONCE HAD
The first version counted any 1% move away from a level as a "reversal", in either direction,
and reported respect rates of 96-98% for every ratio. That is not a finding, it is proof the
test was broken: over five sessions a 1% move is close to certain, so every level "worked".
The measure is now bounce-before-break, which gives a number near 50% when levels mean
nothing - and that is what the data shows.

OUTPUT FILE
docs/gann_fib.json. It must NOT write docs/levels.json: that file holds pivot and Camarilla
levels and the Levels tab reads its rows. Writing here replaced it with a different schema and
blanked the whole page behind "Could not load data.json".
"""
import json, os, sys

SRC = "docs/series.json"      # 120 daily closes per symbol
OUT = "docs/gann_fib.json"
TOUCH_PCT = 0.015             # a close within 1.5% counts as a touch - support is a ZONE
MOVE_PCT = 1.0                # bounce/break threshold
HORIZON = 5
MIN_TOUCHES = 20
MAX_SYMBOLS = 400

FIB = [0.236, 0.382, 0.5, 0.618, 0.786]
GANN = [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]


def swing(closes):
    n = len(closes)
    if n < 40:
        return None
    lo_i = min(range(n), key=lambda i: closes[i])
    hi_i = max(range(n), key=lambda i: closes[i])
    if lo_i == hi_i:
        return None
    return {"low": closes[lo_i], "high": closes[hi_i]}


def respect(closes, level):
    """Bounce or break - whichever came first. The only measure that means anything."""
    if level <= 0:
        return {"touches": 0, "bounces": 0, "breaks": 0, "pct": None}
    up = level * (1 + MOVE_PCT / 100.0)
    down = level * (1 - MOVE_PCT / 100.0)
    touches = bounces = breaks = 0
    n = len(closes)
    i = 0
    while i < n - 1:
        c = closes[i]
        if c > 0 and abs(c - level) / level <= TOUCH_PCT:
            touches += 1
            for j in range(i + 1, min(i + 1 + HORIZON, n)):
                if closes[j] >= up:
                    bounces += 1
                    break
                if closes[j] <= down:
                    breaks += 1
                    break
            i += HORIZON       # do not count the same approach twice
        else:
            i += 1
    decided = bounces + breaks
    return {"touches": touches, "bounces": bounces, "breaks": breaks,
            "pct": round(bounces / decided * 100, 1) if decided else None}


def main():
    if not os.path.exists(SRC):
        print("no %s" % SRC)
        json.dump({"available": False, "count": 0}, open(OUT, "w"), separators=(",", ":"))
        return 0

    d = json.load(open(SRC))
    raw = d.get("series") or {}
    series = {}
    for k, v in raw.items():
        if not v:
            continue
        # series.json holds bare closes; charts.json holds [month, price] pairs. Accept both.
        if isinstance(v[0], (list, tuple)):
            vals = [x[1] for x in v if isinstance(x, (list, tuple)) and len(x) == 2 and x[1]]
        else:
            vals = [x for x in v if isinstance(x, (int, float))]
        if len(vals) >= 40:
            series[k] = vals
    print("  %d symbols with usable closes" % len(series))

    out = {"available": True, "updated": d.get("updated"), "count": 0,
           "symbols": {}, "by_ratio": [], "note": "", "cautions": {}}
    agg = {}

    syms = sorted(series.items(), key=lambda kv: -len(kv[1]))[:MAX_SYMBOLS]
    for sym, closes in syms:
        sw = swing(closes)
        if not sw or not (sw["high"] > sw["low"]):
            continue
        lo, hi = sw["low"], sw["high"]
        span = hi - lo
        levels = []
        for kind, ratios in (("fib", FIB), ("gann", GANN)):
            for f in ratios:
                lv = round(lo + span * f, 2)
                r = respect(closes, lv)
                a = agg.setdefault((kind, f), {"touches": 0, "bounces": 0, "breaks": 0})
                a["touches"] += r["touches"]
                a["bounces"] += r["bounces"]
                a["breaks"] += r["breaks"]
                levels.append([kind, f, lv, r["touches"],
                               r["pct"] if r["touches"] >= MIN_TOUCHES else None])
        keep = [x for x in levels if x[3] > 0]
        if not keep:
            continue
        keep.sort(key=lambda x: -x[2])
        out["symbols"][sym.replace(".NS", "")] = {
            "last": round(closes[-1], 2),
            "swing_low": round(lo, 2), "swing_high": round(hi, 2),
            "levels": keep,
        }

    rows = []
    for (kind, f), a in agg.items():
        decided = a["bounces"] + a["breaks"]
        if a["touches"] >= MIN_TOUCHES and decided:
            rows.append({"kind": kind, "ratio": f, "touches": a["touches"],
                         "bounces": a["bounces"], "breaks": a["breaks"],
                         "held_pct": round(a["bounces"] / decided * 100, 1)})
    rows.sort(key=lambda x: -x["held_pct"])
    out["by_ratio"] = rows
    out["count"] = len(out["symbols"])

    if rows:
        best, worst = rows[0], rows[-1]
        out["ratio_finding"] = (
            "Across every stock, the %s %.1f%% zone was held %.1f%% of the time (%s touches, "
            "bounce before break); the weakest, %s %.1f%%, held %.1f%% (%s touches). A rate near "
            "50%% would mean the level is no better than a coin toss."
            % (best["kind"], best["ratio"] * 100, best["held_pct"], f"{best['touches']:,}",
               worst["kind"], worst["ratio"] * 100, worst["held_pct"], f"{worst['touches']:,}"))

    out["note"] = ("Fibonacci retracements and Gann eighths for %d stocks. For each: how often "
                   "price reached it, and whether a BOUNCE of %.0f%% came before a BREAK of %.0f%%, "
                   "within %d sessions. Below %d touches the rate is withheld."
                   % (out["count"], MOVE_PCT, MOVE_PCT, HORIZON, MIN_TOUCHES))
    out["cautions"] = {
        "description_not_prediction": ("A held rate describes the past. It is not a promise that "
                                       "the level holds next time."),
        "coin_toss_test": ("A rate near 50% means the level is no better than a coin toss. That "
                           "is the honest baseline to read every row against."),
        "closes_only": ("Built from closing prices, and a touch means the close came within "
                        "%.1f%% of the level - a zone, not a hairline." % (TOUCH_PCT * 100)),
        "no_astrology": ("Gann eighths and Fibonacci ratios are arithmetic on a price range. "
                         "Nothing here uses planetary positions or dates."),
    }

    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d stocks, %d ratios measured" % (out["count"], len(rows)))
    for r in rows[:4]:
        print("     %-4s %5.1f%%  held %5.1f%%  touches %6d"
              % (r["kind"], r["ratio"] * 100, r["held_pct"], r["touches"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
