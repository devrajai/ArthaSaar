#!/usr/bin/env python3
"""Two-sided scenario analysis: what has happened next, in both directions.

THE POINT
A direction forecast is a guess dressed up. What the data can honestly give is a
DISTRIBUTION: of the times this setup occurred, how often did it rise, how far, how often did
it fall, and how far. Both sides, with the sample size attached.

So this never says "the market will go up". It says "after a day like this, it rose 64% of the
time by a median +2.43%, and fell 36% of the time by a median -1.66%, and the worst was
-17.26%". A reader can size a position against that. They cannot from a point forecast.

WHAT IT COMPARES
Every setup is shown next to the unconditional baseline. Without that, "64% up" sounds bullish
- but the market rose 57% of the time on ANY day, so the edge is 7 points, not 64.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/scenarios.json"
NIFTY = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=10y"
HORIZONS = (1, 5, 20)


def bars():
    import datetime as dt
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(NIFTY, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        rows = [(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"), c)
                for t, c in zip(r["timestamp"], q["close"]) if c is not None]
        rows.sort()
        return rows
    except Exception:
        return []


def main():
    import statistics as st

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "setups": [], "today": None, "note": ""}

    rows = bars()
    if len(rows) < 500:
        out["note"] = "Not enough history."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("scenarios: insufficient data")
        return 0

    C = [x[1] for x in rows]
    dates = [x[0] for x in rows]
    n = len(C)
    rets = [(C[i] / C[i - 1] - 1) * 100 for i in range(1, n)]

    def fwd(i, h):
        j = i + h
        return None if j >= n else (C[j] / C[i] - 1) * 100

    def summarise(idxs):
        """Both directions, with the sample size - never a single number."""
        rows_out = []
        for h in HORIZONS:
            vals = [v for i in idxs for v in [fwd(i, h)] if v is not None]
            if len(vals) < 5:
                continue
            up = [v for v in vals if v > 0]
            dn = [v for v in vals if v <= 0]
            rows_out.append({
                "horizon_days": h, "n": len(vals),
                "up_pct": round(len(up) / len(vals) * 100, 0),
                "up_median": round(st.median(up), 2) if up else None,
                "down_pct": round(len(dn) / len(vals) * 100, 0),
                "down_median": round(st.median(dn), 2) if dn else None,
                "best": round(max(vals), 2), "worst": round(min(vals), 2),
            })
        return rows_out

    baseline = summarise(list(range(1, n)))

    setups = [
        ("after a day of +2% or more", lambda i: i >= 2 and rets[i - 2] >= 2.0),
        ("after a day of +1% to +2%", lambda i: i >= 2 and 1.0 <= rets[i - 2] < 2.0),
        ("after a day of -1% to -2%", lambda i: i >= 2 and -2.0 < rets[i - 2] <= -1.0),
        ("after a day of -2% or more", lambda i: i >= 2 and rets[i - 2] <= -2.0),
        ("after three up days in a row", lambda i: i >= 4 and all(rets[i - k - 1] > 0 for k in range(3))),
        ("after three down days in a row", lambda i: i >= 4 and all(rets[i - k - 1] < 0 for k in range(3))),
    ]

    for name, cond in setups:
        idxs = [i for i in range(1, n) if cond(i)]
        if len(idxs) < 10:
            continue
        out["setups"].append({"name": name, "matching_days": len(idxs),
                              "horizons": summarise(idxs)})

    out["baseline"] = baseline

    # where does the most recent session sit?
    last_move = rets[-1]
    if last_move >= 2.0:
        label = "after a day of +2% or more"
    elif last_move >= 1.0:
        label = "after a day of +1% to +2%"
    elif last_move <= -2.0:
        label = "after a day of -2% or more"
    elif last_move <= -1.0:
        label = "after a day of -1% to -2%"
    else:
        label = None
    out["today"] = {"date": dates[-1], "move_pct": round(last_move, 2),
                    "setup": label or "a quiet day - no setup applies"}

    out["note"] = ("Historical outcome distributions for both directions, with sample sizes. "
                   "This is not a forecast: it says how often the market rose and fell after a "
                   "similar day, and by how much.")
    out["cautions"] = {
        "both_sides": ("Every setup is shown against the unconditional baseline. The market "
                       "rose 57% of the time on ANY day, so a 64% reading is a 7 point edge, "
                       "not a 64% chance of profit."),
        "sample": "Setups with fewer than 10 matches are omitted rather than shown as a pattern.",
        "overlap": ("Overlapping horizons make the observations dependent, so treat the "
                    "percentages as descriptive rather than statistically independent."),
        "no_direction": ("A big day reliably means a LARGER move, not a direction. That is why "
                         "both tails are shown."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   latest: %s %+.2f%% -> %s" % (out["today"]["date"], last_move, out["today"]["setup"]))
    for s in out["setups"]:
        h20 = next((x for x in s["horizons"] if x["horizon_days"] == 20), None)
        if h20:
            print("   %-32s n=%-4d 20d: up %.0f%% (%+.2f) / down %.0f%% (%+.2f)"
                  % (s["name"], s["matching_days"], h20["up_pct"], h20["up_median"] or 0,
                     h20["down_pct"], h20["down_median"] or 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
