#!/usr/bin/env python3
"""Market case studies, with real numbers from our own 2019-2026 archive.

One page per event: what fell, how far, how many stocks fell, and how long recovery took.
This teaches a beginner what a bad week actually feels like, using their own market rather
than an American example.

WHY AN EQUAL-WEIGHT MEDIAN, NOT THE NIFTY
The Nifty is 50 large caps. A beginner's portfolio is not. The median of every listed stock
is a fairer picture of what an ordinary portfolio did, and it is the number that makes a
crash feel real: on 4 June 2024 the average stock fell 5.9% and 1,820 of 1,925 fell - that is
what the day was like if you owned stocks rather than an index fund.

A MISTAKE THIS AVOIDS
The obvious way to find "the 2020 crash" is max and min over the year. That is wrong: the
median in August 2020 was higher than in January, so the max lands AFTER the trough and the
fall reads backwards. The peak must be searched only BEFORE the trough.
"""
import json, os, sys
from datetime import datetime, timezone

ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
OUT = "docs/cases.json"

# each event: label, peak window, trough window, and a short honest description
EVENTS = [
    {"id": "covid", "label": "The March 2020 crash",
     "peak": ("2020-01-01", "2020-03-05"), "trough": ("2020-03-05", "2020-04-15"),
     "recover_to": ("2020-04-15", "2021-06-30"),
     "about": "The Covid sell-off. India went into lockdown on 25 March 2020; the market "
              "bottomed the day before."},
    {"id": "election2024", "label": "4 June 2024 - election result day",
     "single": ["2024-06-03", "2024-06-04", "2024-06-05"],
     "about": "The day the general election result came in with a smaller majority than the "
              "exit polls had suggested. Index futures had priced a landslide."},
    {"id": "adani2023", "label": "January 2023 - the Adani report",
     "single": ["2023-01-24", "2023-01-25", "2023-01-27", "2023-01-30", "2023-01-31",
                "2023-02-01", "2023-02-02", "2023-02-03"],
     "about": "A short-seller report on the Adani group. The group's own stocks fell far "
              "more than the market; this is the average of every listed stock."},
]


def main():
    import duckdb

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "cases": [], "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("cases: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1400MB'")

    # daily equal-weight median close across every listed stock
    med = con.execute("""
      SELECT CAST(date AS VARCHAR) d, median(close) m, COUNT(*) n
      FROM read_parquet(?) WHERE close > 0 GROUP BY d ORDER BY d
    """, [arch]).fetchall()
    med = [(d, float(m), int(n)) for d, m, n in med if m]
    print("  median series: %d sessions (%s to %s)" % (len(med), med[0][0], med[-1][0]))

    # daily breadth: how many stocks fell, and the average move
    daily = {}
    for r in con.execute("""
      WITH d AS (SELECT CAST(date AS VARCHAR) dd, symbol, close
                 FROM read_parquet(?) WHERE close > 0),
           w AS (SELECT dd, symbol, close,
                        LAG(close) OVER (PARTITION BY symbol ORDER BY dd) prev FROM d)
      SELECT dd, COUNT(*), AVG((close - prev) / prev), SUM(CASE WHEN close < prev THEN 1 ELSE 0 END)
      FROM w WHERE prev IS NOT NULL AND prev > 0 GROUP BY dd
    """, [arch]).fetchall():
        daily[r[0]] = {"n": int(r[1]), "avg_pct": round(float(r[2]) * 100, 2),
                       "fell": int(r[3])}
    con.close()
    print("  breadth days: %d" % len(daily))

    idx = {d: i for i, (d, _, _) in enumerate(med)}
    val = {d: m for d, m, _ in med}

    for ev in EVENTS:
        case = {"id": ev["id"], "label": ev["label"], "about": ev["about"]}

        if "single" in ev:
            days = []
            for d in ev["single"]:
                if d in daily:
                    days.append({"date": d, **daily[d]})
            if not days:
                continue
            worst = min(days, key=lambda x: x["avg_pct"])
            case.update({
                "kind": "days",
                "days": days,
                "worst": worst,
                "summary": ("On %s the average stock moved %+.1f%% and %d of %d fell."
                            % (worst["date"], worst["avg_pct"], worst["fell"], worst["n"])),
            })
            out["cases"].append(case)
            print("  %-14s worst %s %+.2f%% (%d of %d fell)"
                  % (ev["id"], worst["date"], worst["avg_pct"], worst["fell"], worst["n"]))
            continue

        # peak searched only BEFORE the trough - the mistake the docstring warns about
        pw = [v for d, v, _ in med if ev["peak"][0] <= d <= ev["peak"][1]]
        tw = [(d, v) for d, v, _ in med if ev["trough"][0] <= d <= ev["trough"][1]]
        if not pw or not tw:
            continue
        peak_val = max(pw)
        trough_d, trough_val = min(tw, key=lambda x: x[1])
        peak_d = max((d for d, v, _ in med
                      if ev["peak"][0] <= d <= ev["peak"][1] and v == peak_val), default=None)

        # recovery: first session after the trough back at the pre-crash peak
        rec = next((d for d, v, _ in med if d > trough_d and v >= peak_val), None)
        rec_days = None
        if rec and peak_d and trough_d in idx and rec in idx:
            rec_days = idx[rec] - idx[trough_d]

        case.update({
            "kind": "crash",
            "peak_date": peak_d, "peak": round(peak_val, 1),
            "trough_date": trough_d, "trough": round(trough_val, 1),
            "fall_pct": round((trough_val / peak_val - 1) * 100, 1),
            "recovered": rec,
            "sessions_to_recover": rec_days,
            "summary": ("The median stock fell %.1f%% from %s to %s%s."
                        % ((trough_val / peak_val - 1) * 100, peak_d, trough_d,
                           (", and took %d sessions to get back" % rec_days) if rec_days else
                           (", and had not recovered by %s" % med[-1][0] if not rec else ""))),
        })
        out["cases"].append(case)
        print("  %-14s peak %s %.1f -> trough %s %.1f  (%.1f%%)  recovered %s"
              % (ev["id"], peak_d, peak_val, trough_d, trough_val,
                 (trough_val / peak_val - 1) * 100, rec))

    out["count"] = len(out["cases"])
    out["note"] = ("What actually happened, measured on the median listed stock rather than "
                   "the Nifty, because a beginner's portfolio is not 50 large caps.")
    out["cautions"] = {
        "median": "Equal-weight median of every listed stock that day, not an index.",
        "survivorship": ("Only stocks listed today are included. Real falls were slightly "
                         "worse than shown."),
        "not_advice": "Past crashes do not predict the next one's size or timing.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB  |  %d cases" % (OUT, os.path.getsize(OUT) / 1024, out["count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
