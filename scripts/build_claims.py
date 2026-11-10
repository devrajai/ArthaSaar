#!/usr/bin/env python3
"""Claim checker: what history says about a move of this size in this much time.

WHY THIS EXISTS
A video says "Nifty 28,000". A message says "this stock will double in a month". Neither
number means anything without two things attached: how far away it is, and by when. This
turns any claim into those two numbers and then answers it from 10 years of sessions.

For every combination of move size and horizon it publishes the share of past occasions that
move actually happened - and the share that happened in the OPPOSITE direction over the same
horizon, because a page that only reports the upside is an advertisement.

WHAT IT DOES NOT DO
  It does not say whether the claim will happen. It says how often something like it happened
  before, with the count it came from.
  It does not adjust for the fact that the past ten years contained one extraordinary rally.
"""
import json, statistics, sys

SRC = "docs/history.json"
OUT = "docs/claims.json"

# moves to test, in percent. Up and down are measured separately.
MOVES = [2, 3, 5, 8, 10, 12, 15, 20, 25, 30, 40, 50]
# horizons in trading sessions
HORIZONS = [5, 10, 21, 63, 126, 252]
MIN_SAMPLE = 100


def main():
    try:
        d = json.load(open(SRC))
    except Exception:
        print("no %s - nothing to build" % SRC)
        json.dump({"available": False}, open(OUT, "w"), separators=(",", ":"))
        return 0

    rows = d.get("sessions") or d.get("rows") or []
    closes = [r["c"] for r in rows if isinstance(r, dict) and r.get("c")]
    dates = [r.get("d") for r in rows if isinstance(r, dict) and r.get("c")]
    if len(closes) < 300:
        print("only %d sessions - not enough history" % len(closes))
        json.dump({"available": False}, open(OUT, "w"), separators=(",", ":"))
        return 0

    last = closes[-1]
    out = {
        "available": True,
        "index": "Nifty 50",
        "last": round(last, 2),
        "as_of": dates[-1] if dates else None,
        "sessions": len(closes),
        "first": dates[0] if dates else None,
        "moves": MOVES, "horizons": HORIZONS,
        "up": {}, "down": {},
        "note": "", "cautions": {},
    }

    for h in HORIZONS:
        up_row, down_row = {}, {}
        n = len(closes) - h
        if n < MIN_SAMPLE:
            continue
        for m in MOVES:
            hits_up = hits_dn = 0
            for i in range(n):
                r = (closes[i + h] / closes[i] - 1) * 100
                if r >= m:
                    hits_up += 1
                if r <= -m:
                    hits_dn += 1
            up_row[str(m)] = round(hits_up / n * 100, 1)
            down_row[str(m)] = round(hits_dn / n * 100, 1)
        out["up"][str(h)] = up_row
        out["down"][str(h)] = down_row

    # what a reader most often wants: the median and the spread over each horizon
    med = {}
    for h in HORIZONS:
        moves = [(closes[i + h] / closes[i] - 1) * 100 for i in range(len(closes) - h)]
        if len(moves) < MIN_SAMPLE:
            continue
        moves.sort()
        med[str(h)] = {
            "median": round(statistics.median(moves), 1),
            "p10": round(moves[int(len(moves) * 0.10)], 1),
            "p90": round(moves[int(len(moves) * 0.90)], 1),
            "worst": round(moves[0], 1),
            "best": round(moves[-1], 1),
        }
    out["spread"] = med

    one_year = out["up"].get("252", {})
    six = out["up"].get("126", {})
    if one_year.get("12") is not None:
        out["note"] = (
            "Nifty closed at %s on %s. Over %d sessions, a move of +12%% happened %.1f%% of the "
            "time within a year and %.1f%% within six months. The same table gives the chance "
            "of a fall of the same size."
            % (f"{last:,.0f}", out["as_of"], len(closes),
               one_year.get("12"), six.get("12") or 0))
    else:
        out["note"] = "Base rates for %d moves over %d horizons." % (len(MOVES), len(HORIZONS))

    out["cautions"] = {
        "not_a_forecast": ("This is how often a move happened before. It is not a probability "
                           "for this occasion - the conditions today are not the average of the "
                           "last ten years."),
        "one_big_rally": ("The window contains one extraordinary rally. A horizon that includes "
                          "it will look kinder than a normal decade."),
        "opposite_side": ("Every upside figure has a matching downside figure. A claim that "
                          "quotes only the upside has quoted half the data."),
        "closes_only": "Measured on closing prices, so intraday extremes are not counted.",
    }

    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s" % OUT)
    print("   %s" % out["note"])
    print("   horizons:", list(out["up"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
