#!/usr/bin/env python3
"""Event-day moves: what actually happens when a known event lands.

THE QUESTION
A big move is obvious after the close. The useful question is what to EXPECT on a day whose
date is already known - a budget, an election result, a results announcement - so size and
stops can be set before it, not after.

TWO STUDIES HERE

1. MARKET-WIDE EVENTS (Nifty, 10 years)
   For dates that are on the calendar in advance, the measured move on the day, and the
   spread of outcomes. This turns "budget days are volatile" into a number.

2. RESULTS-DAY MOVES (every stock, one full season)
   NSE publishes every quarterly filing with the date it was broadcast. Matching those to our
   own price archive gives the actual move on results day for ~2,000 companies, which can be
   compared with how those same stocks move on an ordinary day.

WHY THE COMPARISON MATTERS
"Reliance moved 11.6% on results" is one observation. What makes it interpretable is knowing
that the median stock moves ~1% on an ordinary day and ~4% on a results day - so an 11.6%
move is a genuine outlier rather than the normal response.

SOURCES
  Nifty daily bars      Yahoo Finance (delayed, unofficial)
  Results dates         NSE corporates-financial-results API, broadcastDate field
  Price archive         our own split-adjusted candle store
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/events.json"
ARCHIVE = ("data/candles/daily_adj.parquet", "data/candles/daily.parquet")
CONFIG = "config/event_days.json"
RESULTS_API = ("https://www.nseindia.com/api/corporates-financial-results"
               "?index=equities&period=Quarterly")
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "application/json, text/plain, */*",
      "Referer": "https://www.nseindia.com/"}
NIFTY = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=10y"


def nifty_bars():
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


def results_dates():
    """symbol -> list of broadcast dates (YYYY-MM-DD)."""
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(RESULTS_API, headers=UA), timeout=120).read())
    except Exception as e:
        print("  results API: %s" % type(e).__name__)
        return {}
    out = {}
    for x in d:
        sym = x.get("symbol")
        raw = str(x.get("broadCastDate") or "").strip()[:11]
        if not sym or not raw:
            continue
        try:
            from datetime import datetime as dt
            iso = dt.strptime(raw, "%d-%b-%Y").strftime("%Y-%m-%d")
        except Exception:
            continue
        out.setdefault(sym, set()).add(iso)
    return {k: sorted(v) for k, v in out.items()}


def main():
    import statistics as st

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "market_events": [], "event_summary": [], "results": None, "note": ""}

    # ---------- 1. market-wide events ----------
    bars = nifty_bars()
    if bars:
        idx = {d: i for i, (d, _) in enumerate(bars)}
        try:
            cfg = json.load(open(CONFIG)).get("events") or []
        except Exception:
            cfg = []
        dates_sorted = [d for d, _ in bars]
        for ev in cfg:
            d = ev.get("date")
            # If the event fell on a non-trading day the market reacts on the NEXT session.
            # 1 Feb 2020 was a Saturday and 1 Feb 2025 was a Saturday, so looking only at
            # the event date would silently drop the two most interesting budget days.
            i = idx.get(d)
            if i is None:
                nxt = next((k for k, dd in enumerate(dates_sorted) if dd >= d), None)
                i = nxt
                note = "next session"
            else:
                note = ""
            if i is None or i == 0:
                continue
            move = (bars[i][1] / bars[i - 1][1] - 1) * 100
            out["market_events"].append({"date": dates_sorted[i], "kind": ev.get("kind"),
                                         "label": ev.get("label"),
                                         "scheduled": d, "note": note,
                                         "nifty_pct": round(move, 2)})
        # per-kind summary
        by = {}
        for e in out["market_events"]:
            by.setdefault(e["kind"], []).append(e["nifty_pct"])
        for k, v in by.items():
            out["event_summary"].append({
                "kind": k, "n": len(v),
                "median_abs_pct": round(st.median([abs(x) for x in v]), 2),
                "max_abs_pct": round(max(abs(x) for x in v), 2),
                "up_share_pct": round(sum(1 for x in v if x > 0) / len(v) * 100, 0),
            })

    # ---------- 2. results-day moves ----------
    arch = next((p for p in ARCHIVE if os.path.exists(p)), None)
    rd = results_dates()
    if arch and rd:
        import duckdb
        con = duckdb.connect()
        con.execute("SET threads=1")
        con.execute("SET memory_limit='1400MB'")

        # The median ordinary move, computed in SQL. Holding 3.5 million floats in Python
        # to take a median of them ran out of memory - the database does it in one pass.
        normal_med = con.execute("""
          WITH d AS (SELECT CAST(date AS VARCHAR) dd, symbol, close
                     FROM read_parquet(?) WHERE close > 0),
               w AS (SELECT dd, symbol, close,
                            LAG(close) OVER (PARTITION BY symbol ORDER BY dd) prev FROM d),
               m AS (SELECT (close - prev) / prev * 100 AS mv FROM w
                     WHERE prev IS NOT NULL AND prev > 0)
          SELECT median(abs(mv)) FROM m
        """, [arch]).fetchone()[0]

        # Only the (symbol, date) pairs we actually need: a results season is ~2,000 symbols
        # on ~84 dates, so this is a small filter rather than the whole archive.
        wanted = []
        for sym, dates in rd.items():
            base = sym.replace("-", "").upper()
            for d in dates:
                wanted.append((d, base))
        con.execute("CREATE TEMP TABLE want(date VARCHAR, symbol VARCHAR)")
        con.executemany("INSERT INTO want VALUES (?, ?)", wanted)

        rows = con.execute("""
          WITH d AS (SELECT CAST(date AS VARCHAR) dd, symbol, close
                     FROM read_parquet(?) WHERE close > 0),
               w AS (SELECT dd, symbol, close,
                            LAG(close) OVER (PARTITION BY symbol ORDER BY dd) prev FROM d),
               m AS (SELECT dd, symbol, (close - prev) / prev * 100 AS mv FROM w
                     WHERE prev IS NOT NULL AND prev > 0)
          SELECT m.dd, m.symbol, m.mv
          FROM m JOIN want ON want.date = m.dd AND want.symbol = m.symbol
        """, [arch]).fetchall()
        con.close()

        on_results = [abs(float(mv)) for _, _, mv in rows]
        matched = len(on_results)

        if on_results:
            out["results"] = {
                "filings_matched": matched,
                "companies": len(rd),
                "median_abs_move_pct": round(st.median(on_results), 2),
                "mean_abs_move_pct": round(st.mean(on_results), 2),
                "share_over_5pct": round(sum(1 for x in on_results if x > 5) / len(on_results) * 100, 1),
                "share_over_10pct": round(sum(1 for x in on_results if x > 10) / len(on_results) * 100, 1),
                "normal_median_abs_move_pct": round(float(normal_med), 2),
            }
            r = out["results"]
            r["expansion_vs_normal"] = round(r["median_abs_move_pct"] / r["normal_median_abs_move_pct"], 2)

    out["note"] = ("Measured moves on dates that were known in advance. This describes what has "
                   "happened on such days; it does not forecast the next one, and it says nothing "
                   "about direction unless the table shows it.")
    out["cautions"] = {
        "direction": ("A results day reliably means a LARGER move, not a particular direction. "
                      "The distribution is two-sided."),
        "sample": ("Market-wide event kinds have only a handful of observations each - a median "
                   "over 5 budget days is a description, not a law."),
        "timing": ("Results filed after the close show up the next session. Where a filing time "
                   "was ambiguous the next trading day is used."),
        "sources": "Nifty from Yahoo (unofficial); results dates from NSE filings.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for s in out["event_summary"]:
        print("   %-18s n=%-2d median |move| %.2f%%  max %.2f%%  up %d%%"
              % (s["kind"], s["n"], s["median_abs_pct"], s["max_abs_pct"], s["up_share_pct"]))
    if out["results"]:
        r = out["results"]
        print("   results days: %d filings, median |move| %.2f%% vs %.2f%% normal (%.1fx)"
              % (r["filings_matched"], r["median_abs_move_pct"],
                 r["normal_median_abs_move_pct"], r["expansion_vs_normal"]))
        print("   over 5%%: %.1f%%   over 10%%: %.1f%%" % (r["share_over_5pct"], r["share_over_10pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
