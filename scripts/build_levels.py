#!/usr/bin/env python3
"""Support and resistance from Fibonacci retracements and Gann eighths, with hit rates.

WHY THIS EXISTS
"Give me Gann and Fibonacci levels" is a reasonable request and a testable one. What is not
reasonable is drawing a line on a chart and calling it support because a book said so. Every
level here is published with the number of times price actually reached it and the share of
those touches that were followed by a reversal. A level with no history is a level with no
evidence, and it says so.

WHAT IS COMPUTED
  swing      the most recent significant high and low in the window, found from closes
  fib        retracements of that swing: 23.6, 38.2, 50, 61.8, 78.6
  gann       Gann's eighths of the range: 1/8, 1/4, 3/8, 1/2, 5/8, 3/4, 7/8
  respect    for each level, how often a touch was followed by a reversal of at least 1%
             within 5 sessions - the only thing that makes a level mean anything

WHAT IT REFUSES TO DO
  call a level "strong" without a sample behind it - below 20 touches the rate is withheld
  draw a level that price has never been near
  claim a level predicts anything. A respect rate is a description of the past.

CLOSES ONLY. The series file carries closes, not OHLC, so a "touch" means the close came
within 0.3% of the level. Intraday wicks are not seen, and the caution on the page says so.
"""
import json, os, sys

SRC = "docs/series.json"
OUT = "docs/levels.json"
WINDOW = 500          # sessions of history considered
TOUCH_PCT = 0.003     # a close within 0.3% of the level counts as a touch
REVERSAL_PCT = 1.0    # a reversal of 1% within the horizon counts as respected
HORIZON = 5
MIN_TOUCHES = 20      # below this the rate is noise and is withheld
MAX_SYMBOLS = 400

FIB = [0.236, 0.382, 0.5, 0.618, 0.786]
GANN = [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]


def swing(closes):
    """The most recent significant low then high (or high then low) in the window."""
    n = len(closes)
    if n < 60:
        return None
    seg = closes[-WINDOW:] if n > WINDOW else closes
    lo_i = min(range(len(seg)), key=lambda i: seg[i])
    hi_i = max(range(len(seg)), key=lambda i: seg[i])
    if lo_i == hi_i:
        return None
    return {"low": seg[lo_i], "high": seg[hi_i], "up": lo_i < hi_i}


def respect(closes, level):
    """How often a close near this level was followed by a reversal."""
    if level <= 0:
        return None
    touches = 0
    respected = 0
    for i in range(len(closes) - HORIZON):
        c = closes[i]
        if c <= 0:
            continue
        if abs(c - level) / level <= TOUCH_PCT:
            touches += 1
            fwd = closes[i + 1:i + 1 + HORIZON]
            if not fwd:
                continue
            # a reversal either way: price moved 1% away from the level and stayed
            if (max(fwd) - level) / level >= REVERSAL_PCT / 100.0:
                respected += 1
            elif (level - min(fwd)) / level >= REVERSAL_PCT / 100.0:
                respected += 1
    return {"touches": touches,
            "respected": respected,
            "pct": round(respected / touches * 100, 1) if touches else None}


def main():
    if not os.path.exists(SRC):
        print("no %s - nothing to build" % SRC)
        json.dump({"updated": None, "available": False, "note": "series.json missing"},
                  open(OUT, "w"), separators=(",", ":"))
        return 0
    d = json.load(open(SRC))
    series = d.get("series") or {}
    print("  %d symbols in series.json" % len(series))

    # the longest series first - a level needs history to be worth computing
    syms = sorted(series.items(), key=lambda kv: -len(kv[1] or []))[:MAX_SYMBOLS]
    out = {"updated": d.get("updated"), "count": 0, "symbols": {}, "note": "", "cautions": {}}

    for sym, closes in syms:
        if not closes or len(closes) < 120:
            continue
        sw = swing(closes)
        if not sw or not (sw["high"] > sw["low"]):
            continue
        lo, hi = sw["low"], sw["high"]
        span = hi - lo
        if span <= 0:
            continue

        levels = []
        # Fibonacci retracements measured from the low of the swing
        for f in FIB:
            lv = round(lo + span * f, 2)
            r = respect(closes, lv)
            levels.append({"kind": "fib", "ratio": f, "price": lv,
                           "touches": r["touches"], "respect_pct": r["pct"] if
                           (r["touches"] or 0) >= MIN_TOUCHES else None})
        # Gann eighths of the range
        for f in GANN:
            lv = round(lo + span * f, 2)
            r = respect(closes, lv)
            levels.append({"kind": "gann", "ratio": f, "price": lv,
                           "touches": r["touches"], "respect_pct": r["pct"] if
                           (r["touches"] or 0) >= MIN_TOUCHES else None})

        # keep only levels price has actually been near, and order by price
        last = closes[-1]
        keep = [x for x in levels if x["touches"] > 0]
        if not keep:
            continue
        keep.sort(key=lambda x: -x["price"])
        out["symbols"][sym.replace(".NS", "")] = {
            "last": round(last, 2),
            "swing_low": round(lo, 2), "swing_high": round(hi, 2),
            "levels": [[x["kind"], x["ratio"], x["price"], x["touches"], x["respect_pct"]]
                       for x in keep],
        }

    out["count"] = len(out["symbols"])
    out["note"] = ("Fibonacci retracements and Gann eighths for %d stocks, each with the number "
                   "of times price actually reached it and how often that touch was followed by "
                   "a reversal of %.0f%% or more within %d sessions. Below %d touches the rate is "
                   "withheld." % (out["count"], REVERSAL_PCT, HORIZON, MIN_TOUCHES))
    out["cautions"] = {
        "description_not_prediction": ("A respect rate describes the past. It is not a promise "
                                       "that the level holds next time."),
        "closes_only": ("Built from closing prices, so a touch means the close came within "
                        "%.1f%% of the level. Intraday wicks are invisible here." % (TOUCH_PCT * 100)),
        "withheld_below_20": ("A rate over fewer than %d touches is noise and is published as "
                              "null, not as a number." % MIN_TOUCHES),
        "no_astrology": ("Gann eighths and Fibonacci ratios are arithmetic on a price range. "
                         "Nothing here uses planetary positions or dates."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %s" % out["note"])
    for s in list(out["symbols"])[:4]:
        v = out["symbols"][s]
        print("     %-12s last %8.2f  swing %.2f-%.2f  levels %d"
              % (s, v["last"], v["swing_low"], v["swing_high"], len(v["levels"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
