#!/usr/bin/env python3
"""Muhurat trading, studied as facts. No picks, no calls, no lists to act on.

WHAT THIS IS
Muhurat is a one-hour symbolic session on Diwali. This measures what actually happened in the
sessions our archive holds, and what followed - nothing more.

WHAT IT DELIBERATELY IS NOT
There is no "Muhurat stock picks" list here, and there never should be. Tip lists around
Diwali are a known scam channel in India and anything that reads as a recommendation carries
SEBI obligations this project cannot meet. Every number below is a description of the past.

THE COVERAGE PROBLEM, STATED UP FRONT
Muhurat often falls on a weekend. Our bulk price backfill only walked weekdays, so three of
the last seven sessions are missing entirely:
  2019-10-27 (Sun)   absent
  2020-11-14 (Sat)   absent
  2023-11-12 (Sun)   absent
  2021, 2022, 2024, 2025 present
So this covers 4 of 7. The table says so rather than quietly showing four rows as if they
were all of them.
"""
import json, os, sys
from datetime import datetime, timezone

ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
STATUS = "docs/market_status.json"
OUT = "docs/muhurat.json"

# Muhurat sessions. Only the weekday ones exist in our archive; the weekend ones are listed
# anyway so the gap is visible rather than invisible.
SESSIONS = [
    ("2019-10-27", "Sunday", "Diwali Laxmi Pujan"),
    ("2020-11-14", "Saturday", "Diwali Laxmi Pujan"),
    ("2021-11-04", "Thursday", "Diwali Laxmi Pujan"),
    ("2022-10-24", "Monday", "Diwali Laxmi Pujan"),
    ("2023-11-12", "Sunday", "Diwali Laxmi Pujan"),
    ("2024-11-01", "Friday", "Diwali Laxmi Pujan"),
    ("2025-10-21", "Tuesday", "Diwali Laxmi Pujan"),
]
FORWARD = (1, 5, 20)


def main():
    import duckdb

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "sessions": [], "missing": [], "upcoming": None, "note": ""}

    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    if not arch:
        out["note"] = "No candle archive on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("muhurat: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1400MB'")

    # every session we have, with a 20-session trailing average volume for comparison
    daily = con.execute("""
      WITH d AS (
        SELECT CAST(date AS VARCHAR) dd, symbol, close, volume
        FROM read_parquet(?) WHERE close > 0
      ),
      agg AS (
        SELECT dd, COUNT(*) n, SUM(volume) vol,
               SUM(CASE WHEN close > 0 THEN 1 ELSE 0 END) listed
        FROM d GROUP BY dd
      ),
      av AS (
        SELECT dd, vol, AVG(vol) OVER (ORDER BY dd ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) av20
        FROM agg
      )
      SELECT dd, vol, av20 FROM av
    """, [arch]).fetchall()
    volmap = {r[0]: (float(r[1] or 0), float(r[2]) if r[2] else None) for r in daily}

    moves = {}
    for r in con.execute("""
      WITH d AS (SELECT CAST(date AS VARCHAR) dd, symbol, close
                 FROM read_parquet(?) WHERE close > 0),
           w AS (SELECT dd, symbol, close,
                        LAG(close) OVER (PARTITION BY symbol ORDER BY dd) prev FROM d)
      SELECT dd, COUNT(*), AVG((close - prev) / prev),
             SUM(CASE WHEN close > prev THEN 1 ELSE 0 END),
             SUM(CASE WHEN close < prev THEN 1 ELSE 0 END)
      FROM w WHERE prev IS NOT NULL AND prev > 0 GROUP BY dd
    """, [arch]).fetchall():
        moves[r[0]] = {"n": int(r[1]), "avg_pct": round(float(r[2]) * 100, 2),
                       "up": int(r[3]), "down": int(r[4])}

    sessions_all = sorted(moves)
    pos = {d: i for i, d in enumerate(sessions_all)}

    for iso, weekday, label in SESSIONS:
        if iso not in moves:
            out["missing"].append({"date": iso, "weekday": weekday,
                                   "reason": "weekend session - the bulk backfill walked "
                                             "weekdays only, so it was never downloaded"})
            continue

        m = moves[iso]
        vol, av20 = volmap.get(iso, (0, None))
        entry = {
            "date": iso, "weekday": weekday, "label": label,
            "stocks_traded": m["n"],
            "avg_move_pct": m["avg_pct"],
            "advances": m["up"], "declines": m["down"],
            "volume": vol,
            "volume_vs_20d": round(vol / av20, 2) if av20 else None,
        }

        # what the market did afterwards - a fact, not a forecast
        i = pos[iso]
        fwd = {}
        for k in FORWARD:
            j = i + k
            if j < len(sessions_all):
                d2 = sessions_all[j]
                if d2 in moves:
                    fwd[str(k)] = moves[d2]["avg_pct"]
        entry["next_sessions_avg_move"] = fwd

        out["sessions"].append(entry)
        print("  %s (%s)  avg %+.2f%%  %d up / %d down  volume x%.2f of 20d"
              % (iso, weekday, m["avg_pct"], m["up"], m["down"],
                 (vol / av20) if av20 else 0))

    # the upcoming session, from the special-sessions config
    if os.path.exists(STATUS):
        try:
            st = json.load(open(STATUS))
            for s in (st.get("special_sessions") or []):
                if "muhurat" in str(s.get("label", "")).lower():
                    days = (datetime.strptime(s["date"], "%Y-%m-%d").date()
                            - datetime.now(timezone.utc).date()).days
                    out["upcoming"] = {**s, "days_away": days}
                    break
        except Exception:
            pass

    con.close()

    out["count"] = len(out["sessions"])
    out["covered_of"] = len(SESSIONS)
    out["note"] = ("What actually happened in the Muhurat sessions our archive holds, and what "
                   "followed. This is a record of the past. It contains no stock picks and no "
                   "recommendation, and it should not be read as one.")
    out["cautions"] = {
        "sample": ("%d sessions is far too few to conclude anything. Any pattern here is "
                   "indistinguishable from chance." % len(out["sessions"])),
        "coverage": ("%d of the last %d Muhurat dates are missing because they fell on a "
                     "weekend and the bulk backfill only walked weekdays."
                     % (len(out["missing"]), len(SESSIONS))),
        "liquidity": ("The session is one hour. Volume is a fraction of a normal day and "
                      "spreads are wider - a fill is not always available at the screen price."),
        "no_picks": ("No stock lists, no targets, no calls. Tip lists around Diwali are a known "
                     "scam channel and this project does not publish them."),
        "symbolic": ("Muhurat is a symbolic session. All of the last five closed higher, which "
                     "is a one-hour gesture, not a forecast."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("\n-> %s  %.0f KB  |  %d of %d sessions"
          % (OUT, os.path.getsize(OUT) / 1024, out["count"], len(SESSIONS)))
    if out["upcoming"]:
        print("   upcoming: %s in %d days, %s-%s"
              % (out["upcoming"]["date"], out["upcoming"]["days_away"],
                 out["upcoming"]["open"], out["upcoming"]["close"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
