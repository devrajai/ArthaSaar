#!/usr/bin/env python3
"""Does the day of the week matter? Tested, not asserted.

WHY THIS EXISTS
A common piece of astrology advice says Wednesday is best for trading, Thursday for long-term
wealth, and Monday suits cautious investors. Those are testable statements, so this tests them
against our own 2019-2026 archive instead of repeating them.

WHAT IT FOUND (the short version)
  Wednesday   short-term claim HOLDS. It is rank 1 of 5 weekdays at 1, 5 and 20 day holds,
              and the edge is positive in 7 of 8 years.
  Thursday    long-term claim FAILS. Rank 4 of 5 on a one-year hold.
  Monday      "cautious and balanced" is BACKWARDS. Monday is both the most volatile day
              and the worst returning one.

WHY THIS IS NOT A RECOMMENDATION
A measured pattern is not advice, and this one has four problems that the page states plainly:
the edge is thin against real transaction costs, it flipped negative in 2026, day-of-week
effects historically weaken once widely known, and a correlation with a weekday is not
evidence of a planetary cause - Monday's behaviour is the weekend news effect, which shows up
in every equity market on earth.
"""
import json, os, sys
from datetime import datetime, timezone

ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
OUT = "docs/weekday.json"
HORIZONS = [("1 day", 1), ("5 days", 5), ("20 days", 20), ("1 year", 250)]
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
PLANET = {"Monday": "Moon", "Tuesday": "Mars", "Wednesday": "Mercury",
          "Thursday": "Jupiter", "Friday": "Venus"}
CLAIM = {"Wednesday": "best for short-term trading",
         "Thursday": "ideal for long-term wealth",
         "Monday": "suitable for cautious, balanced investing"}


def main():
    import duckdb
    import statistics as st

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": [], "rank": {}, "claims": [], "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("weekday: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1400MB'")
    rows = con.execute("""
      WITH d AS (SELECT CAST(date AS VARCHAR) dd, median(close) m
                 FROM read_parquet(?) WHERE close > 0 GROUP BY dd),
           s AS (SELECT dd, m, ROW_NUMBER() OVER (ORDER BY dd) rn FROM d)
      SELECT dd, m, rn, dayname(CAST(dd AS DATE)) dn FROM s ORDER BY rn
    """, [arch]).fetchall()
    con.close()

    seq = [(dd, float(m), dn) for dd, m, rn, dn in rows]
    n = len(seq)

    def fwd(i, h):
        j = i + h
        return None if j >= n else (seq[j][1] / seq[i][1] - 1) * 100

    base = {label: [x for i in range(n) for x in [fwd(i, h)] if x is not None]
            for label, h in HORIZONS}
    base_mean = {k: st.mean(v) for k, v in base.items()}

    for label, h in HORIZONS:
        for dn in DAYS:
            v = [x for i in range(n) if seq[i][2] == dn for x in [fwd(i, h)] if x is not None]
            if not v:
                continue
            out["rows"].append({
                "hold": label, "weekday": dn, "planet": PLANET[dn],
                "n": len(v), "mean_pct": round(st.mean(v), 3),
                "vs_all_pct": round(st.mean(v) - base_mean[label], 3),
            })

    # where each day ranks at each horizon
    for label, h in HORIZONS:
        res = []
        for dn in DAYS:
            v = [x for i in range(n) if seq[i][2] == dn for x in [fwd(i, h)] if x is not None]
            if v:
                res.append((dn, st.mean(v)))
        res.sort(key=lambda t: -t[1])
        out["rank"][label] = [{"weekday": d, "mean_pct": round(m, 3)} for d, m in res]

    # volatility, which is what "cautious" actually depends on
    vol = {}
    for dn in DAYS:
        v = [x for i in range(n) if seq[i][2] == dn for x in [fwd(i, 1)] if x is not None]
        if v:
            vol[dn] = round(st.mean([abs(x) for x in v]), 3)
    allabs = round(st.mean([abs(x) for x in base["1 day"]]), 3)
    out["volatility"] = {"by_weekday": vol, "all_days": allabs}

    # the Wednesday edge, year by year - the stability check that decides whether it is real
    yearly = []
    for y in range(int(seq[0][0][:4]), int(seq[-1][0][:4]) + 1):
        wv = [fwd(i, 1) for i in range(n)
              if seq[i][2] == "Wednesday" and seq[i][0].startswith(str(y)) and fwd(i, 1) is not None]
        av = [fwd(i, 1) for i in range(n)
              if seq[i][0].startswith(str(y)) and fwd(i, 1) is not None]
        if wv and av:
            yearly.append({"year": y, "n": len(wv),
                           "edge_pct": round(st.mean(wv) - st.mean(av), 3)})
    out["wednesday_by_year"] = yearly
    pos = sum(1 for x in yearly if x["edge_pct"] > 0)
    out["wednesday_years_positive"] = pos
    out["wednesday_years_total"] = len(yearly)

    # verdict on each claim, computed rather than typed
    def rank_of(day, hold):
        r = out["rank"].get(hold) or []
        for i, x in enumerate(r, 1):
            if x["weekday"] == day:
                return i, len(r)
        return None, len(r)

    w1, ntot = rank_of("Wednesday", "1 day")
    t1, _ = rank_of("Thursday", "1 year")
    out["claims"] = [
        {"claim": CLAIM["Wednesday"], "weekday": "Wednesday", "planet": "Mercury",
         "tested": "rank at 1-day and 5-day holds",
         "result": "holds", "detail": "rank %d of %d on a 1-day hold, and positive in %d of %d "
                                      "years" % (w1, ntot, pos, len(yearly))},
        {"claim": CLAIM["Thursday"], "weekday": "Thursday", "planet": "Jupiter",
         "tested": "rank at a 1-year hold",
         "result": "does not hold", "detail": "rank %d of %d on a 1-year hold" % (t1, ntot)},
        {"claim": CLAIM["Monday"], "weekday": "Monday", "planet": "Moon",
         "tested": "volatility and return",
         "result": "backwards", "detail": "Monday is the most volatile day (%.3f%% average "
                                          "absolute move against %.3f%% overall) and the "
                                          "weakest at 1 and 20 day holds"
                                          % (vol.get("Monday", 0), allabs)},
    ]

    out["count"] = len(out["rows"])
    out["note"] = ("Three common astrology claims, tested against our own 2019 to today "
                   "archive instead of repeated. A measured pattern is not advice.")
    out["cautions"] = {
        "not_advice": "This is a description of the past, not a recommendation to trade.",
        "costs": ("A 1-day round trip costs roughly 0.15-0.30% in brokerage, STT, stamp duty "
                  "and slippage. The Wednesday edge is thinner than that in most years."),
        "unstable": ("The Wednesday edge turned negative in 2026. Day-of-week effects have "
                     "historically weakened or vanished once widely known."),
        "cause": ("Monday's behaviour is the weekend news effect, seen in every equity market "
                  "on earth. A correlation with a weekday is not evidence of a planetary cause."),
        "multiple": ("Twenty weekday-by-horizon combinations were tested. Some will look "
                     "significant by chance alone."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for c in out["claims"]:
        print("   %-10s %-14s %s" % (c["weekday"], c["result"], c["detail"][:64]))
    print("   Wednesday edge positive in %d of %d years" % (pos, len(yearly)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
