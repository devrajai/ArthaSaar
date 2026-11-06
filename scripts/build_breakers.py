#!/usr/bin/env python3
"""Band calibration and range breakers - the evidence, before the features.

WHY THIS COMES FIRST
Every idea in the latest review - a probability calculator, a portfolio cone, an expiry cone -
rests on one unverified assumption: that the model's 10-90 band actually contains about 80%
of outcomes. Nothing has tested that. timesfm_score.json currently reads scored: 0.

A probability calculator that says "65% chance Nifty finishes above 25,000" from an
uncalibrated band is false precision, and it is worst for beginners, who are the audience that
idea is aimed at. So this builds the measurement first. It also produces something useful
immediately: a factual daily list of stocks that closed outside the band the model gave them.

TWO OUTPUTS

1. RANGE BREAKERS - a fact, not a forecast.
   "These 23 stocks moved further than the model thought normal." No probability claim, and
   self-verifying: if the bands are too narrow, breakers pile up and you can see it.

2. BAND COVERAGE - the calibration number.
   Of N forecasts whose horizon has passed, what share of actual closes landed inside the
   10-90 band? A calibrated model gives about 80%. Above 90% means the bands are too wide to
   be useful; below 70% means they are too narrow to be trusted.

WHAT IT WILL NOT DO
Publish a probability until coverage is measured. With zero settled forecasts it reports
"collecting" and says how many are pending, rather than inventing a number.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

LOG = "data/forecast_log.jsonl"
OUT = "docs/breakers.json"
TARGET_COVERAGE = 80.0        # a 10-90 band should contain ~80% of outcomes
MIN_TO_JUDGE = 100            # do not call it calibrated on a handful of cases


def closes(symbol):
    """Daily closes for one symbol from Yahoo."""
    import datetime as dt
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
         + urllib.parse.quote(symbol) + "?interval=1d&range=2y")
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=45).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        return {dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"): c
                for t, c in zip(r["timestamp"], q["close"]) if c is not None}
    except Exception:
        return {}


def read_log():
    out = []
    try:
        for line in open(LOG):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        pass
    return out


def main():
    entries = read_log()
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "runs": len(entries), "settled": 0, "pending": 0,
           "coverage_pct": None, "target_pct": TARGET_COVERAGE,
           "verdict": "collecting", "breakers": [], "by_horizon": [],
           "note": ""}

    if not entries:
        out["note"] = ("No forecasts logged yet, so there is nothing to check. The first "
                       "results appear once a logged horizon has actually passed.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print("breakers: no log yet")
        return 0

    # index of closes per symbol, fetched once
    symbols = set()
    for e in entries:
        for r in (e.get("rows") or []):
            if r.get("symbol"):
                symbols.add(r["symbol"])
    price = {}
    for s in list(symbols)[:400]:          # keep the run bounded
        price[s] = closes(s)

    inside = outside = 0
    per_h = {}
    breakers = []

    for e in entries:
        as_of = e.get("as_of")
        h = e.get("horizon_days") or 21
        if not as_of:
            continue
        settled_rows = 0
        for r in (e.get("rows") or []):
            sym = r.get("symbol")
            ser = price.get(sym) or {}
            dates = sorted(ser)
            if as_of not in dates:
                continue
            i = dates.index(as_of)
            j = i + h
            if j >= len(dates):
                continue                       # horizon has not passed yet
            last = r.get("last")
            lo, hi = r.get("low10_chg_pct"), r.get("high90_chg_pct")
            if last in (None, 0) or lo is None or hi is None:
                continue
            actual_chg = (ser[dates[j]] / last - 1) * 100
            settled_rows += 1
            hit = lo <= actual_chg <= hi
            if hit:
                inside += 1
            else:
                outside += 1
            bucket = per_h.setdefault(h, {"h": h, "inside": 0, "outside": 0})
            bucket["inside" if hit else "outside"] += 1
            if not hit:
                breakers.append({
                    "symbol": sym, "as_of": as_of, "horizon": h,
                    "forecast_band": [round(lo, 2), round(hi, 2)],
                    "actual_chg_pct": round(actual_chg, 2),
                    "beyond_by_pct": round(actual_chg - hi, 2) if actual_chg > hi
                                     else round(lo - actual_chg, 2),
                })
        if settled_rows:
            out["settled"] += settled_rows

    total = inside + outside
    if total:
        out["coverage_pct"] = round(inside / total * 100, 1)
        if total < MIN_TO_JUDGE:
            out["verdict"] = "too few settled forecasts to judge"
        elif out["coverage_pct"] >= TARGET_COVERAGE - 10:
            out["verdict"] = "bands look about right"
        elif out["coverage_pct"] > TARGET_COVERAGE + 10:
            out["verdict"] = "bands are too wide - they contain more than they should"
        else:
            out["verdict"] = "bands are too narrow - outcomes fall outside too often"

    for b in per_h.values():
        t = b["inside"] + b["outside"]
        b["coverage_pct"] = round(b["inside"] / t * 100, 1) if t else None
        out["by_horizon"].append(b)
    out["by_horizon"].sort(key=lambda x: x["h"])

    # the newest unsettled run is the one whose bands are still live
    breakers.sort(key=lambda b: -abs(b["beyond_by_pct"]))
    out["breakers"] = breakers[:60]

    if total == 0:
        out["note"] = ("%d run(s) logged and nothing settled yet - every logged horizon is "
                       "still in the future. No probability is published until coverage has "
                       "actually been measured." % len(entries))
    else:
        out["note"] = ("Of %d forecasts whose horizon has passed, %.1f%% closed inside the "
                       "10-90 band. A calibrated band gives about %.0f%%."
                       % (total, out["coverage_pct"], TARGET_COVERAGE))
    out["cautions"] = {
        "not_a_probability": ("Band width is not a probability. Nothing here estimates the "
                              "chance of a level being reached."),
        "young": ("The record is days old. A coverage figure from a handful of settled "
                  "forecasts is noise, and the verdict says so below %d cases." % MIN_TO_JUDGE),
        "breakers_are_facts": ("A range breaker is a stock that moved further than the model "
                               "expected. It is a fact about the past, not a signal."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s" % OUT)
    print("   runs %d | settled %d | coverage %s | %s"
          % (out["runs"], out["settled"], out["coverage_pct"], out["verdict"]))
    if out["breakers"]:
        print("   %d range breaker(s); largest:" % len(out["breakers"]))
        for b in out["breakers"][:5]:
            print("     %-12s band %s to %s, actual %+.2f%%"
                  % (b["symbol"], b["forecast_band"][0], b["forecast_band"][1],
                     b["actual_chg_pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
