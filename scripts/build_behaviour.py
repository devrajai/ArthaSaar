#!/usr/bin/env python3
"""Money behaviour: what patience is worth, measured instead of asserted.

WHY THIS EXISTS
Most "wealth mindset" content asserts that discipline pays. That is testable on our own
archive, so this tests it. The result is more useful than the assertion because it also says
where the usual argument is wrong.

WHAT IT MEASURES
  1. What buy-and-hold actually returned on the median listed stock, 2019 to today.
  2. What happens if you miss the N best days - the cost of sitting out rallies.
  3. What happens if you miss the N worst days - the reward for dodging crashes.
  4. How often the market sat below a previous peak, and by how much.

A CLAIM THIS PAGE REFUTES - ITS OWN AUTHOR'S
The standard argument is "the best days cluster with the worst, so you cannot dodge one
without missing the other." I expected that and tested it. It is NOT what the data shows: the
median gap between a top-10 day and the nearest bottom-10 day is 16 sessions, and only one of
ten best days falls within five sessions of a worst day. The best days are spread across 2020
to 2026, not stacked against the crashes.

So the honest argument is not that the days are inseparable. It is that you cannot know in
advance which day you are in. Dodging the ten worst would have turned +28.9% into +388.5% -
which is exactly why everyone believes they can do it, and why doing it consistently is a
different matter.
"""
import json, os, sys
from datetime import datetime, timezone

ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
OUT = "docs/behaviour.json"
MISS = (5, 10, 20, 30)


def compound(rs):
    v = 1.0
    for r in rs:
        v *= (1 + r)
    return (v - 1) * 100


def main():
    import duckdb
    import statistics as st

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "missing_best": [], "missing_worst": [], "drawdown": None,
           "clustering": None, "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("behaviour: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1400MB'")
    rows = con.execute("""
      WITH d AS (SELECT CAST(date AS VARCHAR) dd, median(close) m
                 FROM read_parquet(?) WHERE close > 0 GROUP BY dd)
      SELECT dd, m FROM d ORDER BY dd
    """, [arch]).fetchall()
    con.close()

    seq = [(d, float(m)) for d, m in rows]
    if len(seq) < 300:
        out["note"] = "Not enough sessions to say anything."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("behaviour: too little data")
        return 0

    rets = [(seq[i][1] / seq[i - 1][1] - 1) for i in range(1, len(seq))]
    dates = [seq[i][0] for i in range(1, len(seq))]
    base = compound(rets)
    out["period"] = {"from": seq[0][0], "to": seq[-1][0], "sessions": len(seq)}
    out["buy_and_hold_pct"] = round(base, 1)

    order = sorted(range(len(rets)), key=lambda i: -rets[i])       # best first
    worst_order = sorted(range(len(rets)), key=lambda i: rets[i])  # worst first

    for N in MISS:
        drop = set(order[:N])
        r = compound([rets[i] for i in range(len(rets)) if i not in drop])
        out["missing_best"].append({"days": N, "return_pct": round(r, 1),
                                    "vs_hold_pp": round(r - base, 1)})
        dropw = set(worst_order[:N])
        rw = compound([rets[i] for i in range(len(rets)) if i not in dropw])
        out["missing_worst"].append({"days": N, "return_pct": round(rw, 1),
                                     "vs_hold_pp": round(rw - base, 1)})

    # do the best and worst days sit next to each other? (they do not - see the docstring)
    best = set(order[:10])
    worst = set(worst_order[:10])
    gaps = [min(abs(b - w) for w in worst) for b in sorted(best)]
    out["clustering"] = {
        "median_gap_sessions": int(st.median(gaps)),
        "best_within_5_sessions": sum(1 for g in gaps if g <= 5),
        "best_within_10_sessions": sum(1 for g in gaps if g <= 10),
        "conclusion": ("The best and worst days are NOT adjacent. The usual argument that you "
                       "cannot dodge the worst without missing the best does not hold on this "
                       "data. The real problem is that neither is knowable in advance."),
    }

    # drawdown: how much of the time was the market under water, and how deep
    peak = seq[0][1]
    deepest, deepest_date = 0.0, seq[0][0]
    under20 = under30 = 0
    for d, m in seq:
        if m > peak:
            peak = m
        else:
            x = (m / peak - 1) * 100
            if x < deepest:
                deepest, deepest_date = x, d
            if x < -20:
                under20 += 1
            if x < -30:
                under30 += 1
    out["drawdown"] = {
        "deepest_pct": round(deepest, 1),
        "deepest_date": deepest_date,
        "sessions_below_20pct": under20,
        "sessions_below_30pct": under30,
        "pct_sessions_below_20pct": round(under20 / len(seq) * 100, 0),
        "pct_sessions_below_30pct": round(under30 / len(seq) * 100, 0),
    }

    out["note"] = ("Measured on the median listed stock, equal weight, split-adjusted. This is "
                   "a record of what happened, not a prediction, and it is not investment advice.")
    out["cautions"] = {
        "hindsight": ("Every 'missing the N best days' figure is calculated with perfect "
                      "hindsight. Nobody knows on the morning of a day that it will be one of "
                      "the ten best."),
        "survivorship": "Only stocks listed today are included.",
        "median": "The median listed stock, not the Nifty.",
        "not_advice": "A description of the past. Not a recommendation.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   buy and hold: %+.1f%% over %d sessions" % (base, len(seq)))
    print("   miss 10 best : %+.1f%%   miss 10 worst: %+.1f%%"
          % (out["missing_best"][1]["return_pct"], out["missing_worst"][1]["return_pct"]))
    print("   clustering: median gap %d sessions, %d of 10 within 5"
          % (out["clustering"]["median_gap_sessions"],
             out["clustering"]["best_within_5_sessions"]))
    print("   deepest fall %.1f%% on %s; %.0f%% of sessions below a 20%% prior peak"
          % (out["drawdown"]["deepest_pct"], out["drawdown"]["deepest_date"],
             out["drawdown"]["pct_sessions_below_20pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
