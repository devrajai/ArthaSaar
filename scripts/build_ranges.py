#!/usr/bin/env python3
"""Normal ranges, stop-loss noise and level probabilities - measured from history.

WHY HISTORY AND NOT THE MODEL
The last review suggested a probability calculator built on the TimesFM band. That band has
never been tested: timesfm_score.json reads scored: 0. A percentage from an uncalibrated band
is invented.

Ten years of actual sessions do support the same questions honestly. "Nifty finished above
25,000 within 21 sessions in 34% of past periods" is a measured frequency, not a model's
guess, and it needs no calibration.

WHAT THIS PUBLISHES
  normal_range      the 10th, 50th and 90th percentile of 5-day and 21-day moves per symbol.
                    "Most 21-day periods for this stock stay within -9% to +8%."
  stop_noise        how often a stop placed 1%, 2%, 3%, 5% below entry was hit within 5 and
                    21 sessions. Tells a reader whether their stop sits inside ordinary noise.
  levels            for an index, the share of past periods that finished above, or touched,
                    a given percentage move. This is the honest version of a probability
                    calculator.

WHAT IT WILL NOT SAY
Anything about the future. Every number is a frequency in the sample, published with the
sample size beside it.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = "docs/ranges.json"
NIFTY = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=10y"
HORIZONS = (5, 21)
STOPS = (1.0, 2.0, 3.0, 5.0)
LEVELS = (-10, -7, -5, -3, -2, -1, 1, 2, 3, 5, 7, 10)
MAX_SYMBOLS = 400
MIN_HISTORY = 400


def pct(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    i = int(round((len(s) - 1) * q))
    return round(s[max(0, min(i, len(s) - 1))], 2)


def nifty_series():
    import datetime as dt
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(NIFTY, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        rows = sorted([(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"),
                        o, h, l, c)
                       for t, o, h, l, c in zip(r["timestamp"], q["open"], q["high"],
                                                q["low"], q["close"])
                       if None not in (o, h, l, c)])
        return rows
    except Exception as e:
        print("  nifty fetch failed: %s" % type(e).__name__)
        return []


def archive_closes():
    """{symbol: [close,...]} from the candle archive, most-traded first."""
    import glob
    out = {}
    for path in sorted(glob.glob("data/candles/*adj*.parquet")) + \
                sorted(glob.glob("data/candles/*.parquet")):
        try:
            import duckdb
            con = duckdb.connect()
            con.execute("SET threads=1")
            con.execute("SET memory_limit='1400MB'")
            # Order by turnover, not by name. Taking the first 400 alphabetically gave a
            # file full of 20MICRONS and 3MINDIA and no RELIANCE or TCS - the names anyone
            # actually looks up were missing entirely.
            has_vol = "volume" in [c[0] for c in con.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)", [path]).fetchall()]
            if has_vol:
                q = """
                  SELECT symbol FROM (
                    SELECT symbol, COUNT(*) n, AVG(volume) v FROM read_parquet(?)
                    WHERE close > 0 GROUP BY symbol HAVING COUNT(*) >= ?
                  ) ORDER BY v DESC NULLS LAST LIMIT ?
                """
            else:
                q = """
                  SELECT symbol FROM (
                    SELECT symbol, COUNT(*) n FROM read_parquet(?) WHERE close > 0
                    GROUP BY symbol HAVING COUNT(*) >= ?
                  ) ORDER BY symbol LIMIT ?
                """
            syms = [r[0] for r in con.execute(q, [path, MIN_HISTORY, MAX_SYMBOLS]).fetchall()]
            for s in syms:
                rows = con.execute("""
                  SELECT close FROM read_parquet(?) WHERE symbol = ? AND close > 0 ORDER BY date
                """, [path, s]).fetchall()
                if len(rows) >= MIN_HISTORY:
                    out[str(s)] = [float(r[0]) for r in rows]
            con.close()
            if out:
                break
        except Exception as e:
            print("  archive %s: %s" % (path, type(e).__name__))
            continue
    return out


def band(closes):
    """Percentiles and stop-hit rates for one price series."""
    n = len(closes)
    if n < MIN_HISTORY:
        return None
    rec = {"n": n}
    for h in HORIZONS:
        moves = [(closes[i + h] / closes[i] - 1) * 100 for i in range(n - h)]
        rec["p10_%dd" % h] = pct(moves, 0.10)
        rec["p50_%dd" % h] = pct(moves, 0.50)
        rec["p90_%dd" % h] = pct(moves, 0.90)
        rec["worst_%dd" % h] = round(min(moves), 2) if moves else None
        rec["best_%dd" % h] = round(max(moves), 2) if moves else None
    # stop-loss noise: from each entry, was a stop at S% below hit within the horizon?
    for s in STOPS:
        for h in HORIZONS:
            hit = 0
            tot = 0
            for i in range(n - h):
                entry = closes[i]
                stop = entry * (1 - s / 100.0)
                tot += 1
                for j in range(i + 1, i + h + 1):
                    if closes[j] <= stop:
                        hit += 1
                        break
            rec["stop_%g_%dd" % (s, h)] = round(hit / tot * 100) if tot else None
    return rec


def levels(rows):
    """For an index: share of past periods that finished beyond / touched a % move."""
    if len(rows) < MIN_HISTORY:
        return []
    closes = [r[4] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    out = []
    h = 21
    n = len(closes)
    for lv in LEVELS:
        finish = touch = tot = 0
        for i in range(n - h):
            target = closes[i] * (1 + lv / 100.0)
            tot += 1
            end = closes[i + h]
            if (lv > 0 and end >= target) or (lv < 0 and end <= target):
                finish += 1
            hi = max(highs[i + 1:i + h + 1])
            lo = min(lows[i + 1:i + h + 1])
            if (lv > 0 and hi >= target) or (lv < 0 and lo <= target):
                touch += 1
        out.append({"move_pct": lv, "periods": tot,
                    "finished_pct": round(finish / tot * 100) if tot else None,
                    "touched_pct": round(touch / tot * 100) if tot else None})
    return out


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "horizons": list(HORIZONS), "stops": list(STOPS),
           "symbols": {}, "index": None, "note": ""}

    rows = nifty_series()
    if rows:
        out["index"] = {"symbol": "^NSEI", "name": "Nifty 50",
                        "range": band([r[4] for r in rows]),
                        "levels": levels(rows),
                        "first": rows[0][0], "last": rows[-1][0]}

    for sym, cl in archive_closes().items():
        b = band(cl)
        if b:
            out["symbols"][sym] = b

    out["count"] = len(out["symbols"])
    out["note"] = ("Percentile ranges, stop-hit rates and level frequencies measured over the "
                   "sample each series actually has. These are frequencies in past data, not "
                   "forecasts.")
    out["cautions"] = {
        "past_only": ("Every figure is a frequency in past data. It says what happened, not "
                      "what will."),
        "sample": ("The sample size is published beside every figure. A stock with 400 "
                   "sessions and one with 2,000 are not equally informative."),
        "touch_vs_finish": ("Touching a level is roughly twice as likely as finishing beyond "
                            "it, because a price can touch and come back. The two are shown "
                            "separately for that reason."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    if out["index"]:
        r = out["index"]["range"]
        print("   Nifty 21d range: %s%% to %s%% (median %s%%, n=%d)"
              % (r["p10_21d"], r["p90_21d"], r["p50_21d"], r["n"]))
        print("   Nifty stop 2%% hit within 21d: %s%% of entries"
              % r.get("stop_2_21d"))
        lv = {x["move_pct"]: x for x in out["index"]["levels"]}
        if 5 in lv:
            print("   Nifty +5%% in 21d: finished %s%%, touched %s%%"
                  % (lv[5]["finished_pct"], lv[5]["touched_pct"]))
    print("   %d symbols" % out["count"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
