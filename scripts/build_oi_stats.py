#!/usr/bin/env python3
"""Do PCR and max pain actually tell you anything? Tested on 1,930 sessions.

This is not a signal. It is a measurement, and the honest answer may be "barely", which is
worth knowing before anyone puts money behind it.

TWO QUESTIONS
  1. PCR extremes - after the put-call ratio sits in the top or bottom decile of its own
     history, what did the index do over the next 1, 5 and 20 sessions? Compared against
     every other day, so the baseline is the index's own drift rather than zero.
  2. Max pain drift - max pain is the strike where option writers lose least. The claim
     traders make is that price gravitates toward it into expiry. Test: when price sits far
     from max pain, does it move toward it over the following sessions, more than it would
     by chance?

WHAT THIS DELIBERATELY DOES NOT DO
Max pain and the close on the SAME day are computed from the same open interest, so any
same-day "accuracy" is circular - it measures arithmetic, not prediction. Everything here is
FORWARD looking: today's reading against what happened next. That is the only version of the
question that could matter to a trader.
"""
import json, os, sys
from datetime import datetime, timezone

SRC = "data/oi/oi_history.parquet"
CLOSES = ("data/yahoo/NSEI.parquet", "data/yahoo/NSEBANK.parquet")
OUT = "docs/oi_stats.json"
INDICES = ("NIFTY", "BANKNIFTY")
HORIZONS = (1, 5, 20)
MIN_CASES = 20          # below this, publish nothing but a note
FAR_PCT = 0.02          # "far from max pain" = more than 2% away


def pct(a, b):
    return (a / b - 1.0) * 100.0 if b else None


def decile(sorted_vals, q):
    if not sorted_vals:
        return None
    i = min(len(sorted_vals) - 1, max(0, int(q * len(sorted_vals))))
    return sorted_vals[i]


def main():
    import pandas as pd

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "pcr_extremes": {}, "max_pain_drift": {}, "note": ""}

    if not os.path.exists(SRC):
        out["note"] = "No option-chain history on disk yet."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("oi stats: skipped (no history)")
        return 0

    df = pd.read_parquet(SRC)
    print("  %d rows, %s -> %s" % (len(df), df["date"].min(), df["date"].max()))

    # real index closes, so forward returns are measured on the index itself
    closes = {}
    for path in CLOSES:
        if not os.path.exists(path):
            continue
        try:
            y = pd.read_parquet(path)
        except Exception:
            continue
        dcol = next((c for c in ("date", "Date", "index", "ts") if c in y.columns), None)
        ccol = next((c for c in ("close", "Close", "adj_close") if c in y.columns), None)
        if not dcol or not ccol:
            continue
        ser = {}
        for d, c in zip(y[dcol], y[ccol]):
            try:
                k = str(d)[:10]
                v = float(c)
                if v == v and v > 0:
                    ser[k] = v
            except Exception:
                continue
        if ser:
            closes["NIFTY" if "NSEI" in path and "BANK" not in path else "BANKNIFTY"] = ser
            print("  closes for %s: %d" % ("NIFTY" if "NSEI" in path and "BANK" not in path
                                           else "BANKNIFTY", len(ser)))

    # Fallback closes: the parquet carries a real underlying price on the rows where
    # spot_source == 'underlying'. That is only part of the history (the older bhavcopy has
    # no underlying column), so Yahoo is preferred - but a partial real series beats a
    # full fabricated one, and it lets this run stand on its own when Yahoo is unreachable.
    fallback = {}
    if "spot" in df.columns and "spot_source" in df.columns:
        for r in df[df["spot_source"] == "underlying"].itertuples(index=False):
            d = str(getattr(r, "date"))[:10]
            v = getattr(r, "spot")
            if v == v and v:
                fallback.setdefault(getattr(r, "index"), {})[d] = float(v)
        for k, v in fallback.items():
            print("  fallback closes for %s: %d rows (underlying price only)" % (k, len(v)))

    total_cases = 0
    for idx in INDICES:
        g = df[df["index"] == idx].sort_values("date")
        cl = closes.get(idx) or {}
        if not cl:
            cl = fallback.get(idx) or {}
            if cl:
                print("  %s: using the parquet's own underlying prices (no Yahoo file)" % idx)
        rows = []
        for r in g.itertuples(index=False):
            d = str(getattr(r, "date"))[:10]
            rows.append({
                "date": d,
                "pcr": float(getattr(r, "pcr")) if getattr(r, "pcr") == getattr(r, "pcr") else None,
                "max_pain": getattr(r, "max_pain", None),
                "close": cl.get(d),
            })
        # forward returns on the index
        dates = [x["date"] for x in rows]
        for i, x in enumerate(rows):
            for h in HORIZONS:
                j = i + h
                x["fwd%d" % h] = (pct(rows[j]["close"], x["close"])
                                  if j < len(rows) and x["close"] and rows[j]["close"] else None)

        # ---- 1. PCR extremes ----
        valid = [x for x in rows if x["pcr"] is not None]
        if len(valid) >= MIN_CASES * 4:
            pcr_sorted = sorted(x["pcr"] for x in valid)
            lo, hi = decile(pcr_sorted, 0.10), decile(pcr_sorted, 0.90)

            def avg_fwd(subset, h):
                vals = [x["fwd%d" % h] for x in subset if x["fwd%d" % h] is not None]
                return (sum(vals) / len(vals), len(vals)) if len(vals) >= MIN_CASES else (None, len(vals))

            allf = {}
            lowf = {}
            highf = {}
            for h in HORIZONS:
                allf[h] = avg_fwd(valid, h)
                lowf[h] = avg_fwd([x for x in valid if x["pcr"] <= lo], h)
                highf[h] = avg_fwd([x for x in valid if x["pcr"] >= hi], h)

            out["pcr_extremes"][idx] = {
                "days": len(valid),
                "low_cut": round(lo, 3), "high_cut": round(hi, 3),
                "baseline": {str(h): (round(allf[h][0], 3) if allf[h][0] is not None else None,
                                      allf[h][1]) for h in HORIZONS},
                "low": {str(h): (round(lowf[h][0], 3) if lowf[h][0] is not None else None,
                                 lowf[h][1]) for h in HORIZONS},
                "high": {str(h): (round(highf[h][0], 3) if highf[h][0] is not None else None,
                                  highf[h][1]) for h in HORIZONS},
            }
            total_cases += 1

        # ---- 2. max pain drift ----
        # signed gap between price and max pain, then what price did next.
        mp = [x for x in rows if x["max_pain"] and x["close"]]
        if len(mp) >= MIN_CASES * 4:
            for x in mp:
                x["gap_pct"] = pct(x["close"], x["max_pain"])   # +ve = above max pain
            far_above = [x for x in mp if x["gap_pct"] is not None and x["gap_pct"] > FAR_PCT * 100]
            far_below = [x for x in mp if x["gap_pct"] is not None and x["gap_pct"] < -FAR_PCT * 100]

            def drift(subset, h):
                """Mean forward return, signed so a move TOWARD max pain is positive."""
                vals = []
                for x in subset:
                    f = x["fwd%d" % h]
                    if f is None:
                        continue
                    # above max pain: falling is progress; below: rising is progress
                    vals.append(-f if x["gap_pct"] > 0 else f)
                return (sum(vals) / len(vals), len(vals)) if len(vals) >= MIN_CASES else (None, len(vals))

            base = {}
            for h in HORIZONS:
                v = [x["fwd%d" % h] for x in mp if x["fwd%d" % h] is not None]
                base[str(h)] = (round(sum(v) / len(v), 3) if len(v) >= MIN_CASES else None, len(v))

            out["max_pain_drift"][idx] = {
                "days": len(mp),
                "mean_abs_gap_pct": round(sum(abs(x["gap_pct"]) for x in mp
                                              if x["gap_pct"] is not None) / max(1, len(mp)), 2),
                "far_above": {"days": len(far_above),
                              **{str(h): (round(drift(far_above, h)[0], 3)
                                          if drift(far_above, h)[0] is not None else None,
                                          drift(far_above, h)[1]) for h in HORIZONS}},
                "far_below": {"days": len(far_below),
                              **{str(h): (round(drift(far_below, h)[0], 3)
                                          if drift(far_below, h)[0] is not None else None,
                                          drift(far_below, h)[1]) for h in HORIZONS}},
                "baseline_fwd": base,
            }
            total_cases += 1

    out["count"] = total_cases
    out["min_cases"] = MIN_CASES
    out["note"] = ("Forward-looking only: today's PCR or max-pain distance against what the "
                   "index did over the next 1, 5 and 20 sessions. Same-day 'accuracy' would be "
                   "circular, because both are computed from the same open interest.")
    out["cautions"] = {
        "small": "Results under %d cases are not published." % MIN_CASES,
        "baseline": ("Every figure is shown next to the index's own average move over the same "
                     "horizon, so you can see whether the signal adds anything."),
        "survivorship": "Index level only - no stock selection bias.",
        "not_a_signal": ("A historical tendency is not a prediction. If the edge is small "
                         "relative to the spread, it is not tradable after costs."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))

    for idx, s in out["pcr_extremes"].items():
        print("   %s PCR: low<=%.2f, high>=%.2f" % (idx, s["low_cut"], s["high_cut"]))
        for k in ("baseline", "low", "high"):
            v = s[k]
            print("      %-9s 1d %s  5d %s  20d %s" % (
                k, v.get("1"), v.get("5"), v.get("20")))
    for idx, s in out["max_pain_drift"].items():
        print("   %s max pain: mean |gap| %.2f%%, far above %d days, far below %d days"
              % (idx, s["mean_abs_gap_pct"], s["far_above"]["days"], s["far_below"]["days"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
