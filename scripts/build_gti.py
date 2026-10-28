#!/usr/bin/env python3
"""Volume structure: POC, value area, supply/demand zones, accumulation, GTI-style candles.

WHAT THIS IS, AND WHAT IT IS NOT
The commercial indicator described to me computes its Point of Control from intraday volume
distributed across price. We have DAILY bars, so the whole day's volume is placed at that
day's typical price. That is a standard approximation - a volume-by-price profile built from
daily bars - but it is coarser than a true intraday profile. It is labelled as such wherever
it appears, because a POC that looks precise but is built from 20 daily points would be
misleading if presented as tick-level truth.

"Gamma Ray" is a proprietary name and I do not have its formula. What is computed here is a
plain momentum-and-strength composite, named honestly. It is not a claim to replicate that
indicator.

WHAT IS GENUINE
  * POC - the price with the most traded volume in the window. Real, from real volume.
  * Value area (VAH/VAL) - the price band holding 70% of volume. Standard market profile.
  * Supply and demand zones - the heaviest volume nodes away from the POC.
  * Accumulation / distribution - Chaikin's money flow, cumulative and signed.
  * Candle classification - volume and close position against the recent average.

Everything is computed from the same split-adjusted archive the rest of the site uses, so it
is back-testable: the same function runs over any historical window.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/gti.json"
TOP_N = 250          # stocks to publish, by traded value
DAILY_WIN = 20       # sessions for the daily profile
WEEKLY_WIN = 5       # sessions for the weekly profile
ZONE_WIN = 60        # sessions to look for supply/demand
MIN_SESSIONS = 60


def volume_profile(highs, lows, closes, vols, tick_frac=0.001):
    """Volume-by-price. Each day's volume lands at that day's typical price.

    Returns (poc, vah, val, nodes) where nodes is [(price, volume)] heaviest first.
    """
    if not closes:
        return None, None, None, []
    typical = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    ref = typical[-1]
    tick = max(ref * tick_frac, 0.01)
    buckets = {}
    for p, v in zip(typical, vols):
        if v is None or v != v or v <= 0:
            continue
        k = round(p / tick)
        buckets[k] = buckets.get(k, 0.0) + float(v)
    if not buckets:
        return None, None, None, []

    total = sum(buckets.values())
    ordered = sorted(buckets.items(), key=lambda kv: -kv[1])
    poc_key = ordered[0][0]
    poc = poc_key * tick

    # value area: expand out from the POC, adding the heavier neighbour each step, until 70%
    keys = sorted(buckets)
    i = keys.index(poc_key)
    lo = hi = i
    acc = buckets[poc_key]
    target = total * 0.70
    while acc < target and (lo > 0 or hi < len(keys) - 1):
        left = buckets[keys[lo - 1]] if lo > 0 else -1
        right = buckets[keys[hi + 1]] if hi < len(keys) - 1 else -1
        if right >= left:
            hi += 1
            acc += right
        else:
            lo -= 1
            acc += left
    val = keys[lo] * tick
    vah = keys[hi] * tick

    nodes = [(k * tick, v) for k, v in ordered[:40]]
    return poc, vah, val, nodes


def zones_from_nodes(nodes, spot, poc):
    """Heaviest volume nodes away from the POC, split into supply above and demand below."""
    supply, demand = [], []
    for price, vol in nodes:
        if abs(price - poc) / (poc or 1) < 0.002:
            continue                      # the POC itself is not a zone
        if price > spot:
            supply.append({"price": round(price, 2), "volume": int(vol)})
        elif price < spot:
            demand.append({"price": round(price, 2), "volume": int(vol)})
        if len(supply) >= 3 and len(demand) >= 3:
            break
    return supply[:3], demand[:3]


def chaikin(highs, lows, closes, vols):
    """Cumulative Chaikin money flow, plus the 20-session slope as a percentage."""
    ad = 0.0
    series = []
    for h, l, c, v in zip(highs, lows, closes, vols):
        if h is None or l is None or h == l or not v:
            series.append(ad)
            continue
        mfm = ((c - l) - (h - c)) / (h - l)
        ad += mfm * float(v)
        series.append(ad)
    if len(series) < 21:
        return None, None
    recent = series[-20:]
    span = max(abs(x) for x in recent) or 1.0
    slope = (recent[-1] - recent[0]) / span
    state = "accumulation" if slope > 0.15 else ("distribution" if slope < -0.15 else "neutral")
    return round(slope, 3), state


def classify_candles(highs, lows, closes, opens, vols, n=20):
    """GTI-style candle tags over the last n sessions.

    blue  - high demand: up close, heavy volume, closed in the top of its range
    black - supply: down close, heavy volume, closed in the bottom of its range
    yellow- unusual: volume far above average but a narrow range (indecision, often
            before a move)
    """
    if not closes or len(closes) < 22:
        return {"blue": 0, "black": 0, "yellow": 0, "last": None}
    avg_vol = sum(v for v in vols[-21:-1] if v) / max(1, len([v for v in vols[-21:-1] if v]))
    counts = {"blue": 0, "black": 0, "yellow": 0}
    last = None
    for i in range(max(0, len(closes) - n), len(closes)):
        o, h, l, c, v = opens[i], highs[i], lows[i], closes[i], vols[i]
        if None in (o, h, l, c) or not v or not avg_vol or h == l:
            continue
        rng = h - l
        pos = (c - l) / rng
        heavy = v > 1.5 * avg_vol
        tag = None
        if heavy and c > o and pos > 0.6:
            tag = "blue"
        elif heavy and c < o and pos < 0.4:
            tag = "black"
        elif v > 1.8 * avg_vol and rng / (c or 1) < 0.022:
            # Heavy volume with a narrow range: effort without result, often before a move.
            # The first thresholds (2.0x volume, 1.2% range) caught only 2 candles in 5,000,
            # which is not a signal - it is a curiosity.
            tag = "yellow"
        if tag:
            counts[tag] += 1
            last = {"tag": tag, "date": None, "index": i}
    return {"blue": counts["blue"], "black": counts["black"],
            "yellow": counts["yellow"], "last": last}


def momentum_strength(closes):
    """20-session return, and that return divided by realised volatility.

    Deliberately NOT called 'Gamma Ray'. It is momentum and strength, plainly.
    """
    if len(closes) < 21:
        return None, None, None
    ret = closes[-1] / closes[-21] - 1.0
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(len(closes) - 20, len(closes))]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
    vol = (var ** 0.5) * (252 ** 0.5)
    strength = (ret * 100.0) / (vol * 100.0) if vol else None
    return round(ret * 100, 2), (round(vol * 100, 1) if vol else None), \
           (round(strength, 2) if strength is not None else None)


def main():
    import duckdb

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "stocks": {}, "note": "", "cautions": {}}

    arch = "data/candles/daily_adj.parquet"
    if not os.path.exists(arch):
        out["note"] = "No candle archive, so no volume structure is published."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("gti: skipped (no archive)")
        return 0

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1300MB'")
    con.execute("SET preserve_insertion_order=false")

    # Cutoffs computed here, not in SQL: `date` is a DATE column and subtracting an INTERVAL
    # from it yields a TIMESTAMP, which DuckDB refuses to compare against DATE.
    import datetime as dt
    last = con.execute("SELECT max(date) FROM read_parquet(?)", [arch]).fetchone()[0]
    last = dt.date.fromisoformat(str(last)[:10])
    cut90 = (last - dt.timedelta(days=130)).isoformat()
    cut200 = (last - dt.timedelta(days=300)).isoformat()

    # universe: the most heavily traded, so the file stays small and useful
    top = con.execute("""
      SELECT symbol, sum(close * volume) AS tv, count(*) AS n
      FROM read_parquet(?)
      WHERE date >= ?
      GROUP BY 1 HAVING count(*) >= ? ORDER BY tv DESC LIMIT ?
    """, [arch, cut90, MIN_SESSIONS, TOP_N]).fetchall()
    syms = [r[0] for r in top]
    print("  universe: %d symbols" % len(syms))

    ph = ",".join("?" * len(syms))
    df = con.execute("""
      SELECT symbol, date, open, high, low, close, volume
      FROM read_parquet(?)
      WHERE symbol IN (%s) AND date >= ?
      ORDER BY symbol, date
    """ % ph, [arch] + syms + [cut200]).fetchdf()
    con.close()
    print("  loaded %d rows" % len(df))

    for sym, g in df.groupby("symbol", sort=False):
        g = g.dropna(subset=["close"])
        if len(g) < MIN_SESSIONS:
            continue
        h = g["high"].tolist(); l = g["low"].tolist()
        c = g["close"].tolist(); o = g["open"].tolist(); v = g["volume"].tolist()
        spot = c[-1]

        # daily profile on the recent window, weekly on the last 5 sessions
        dpoc, dvah, dval, nodes = volume_profile(
            h[-DAILY_WIN:], l[-DAILY_WIN:], c[-DAILY_WIN:], v[-DAILY_WIN:])
        wpoc, wvah, wval, _ = volume_profile(
            h[-WEEKLY_WIN:], l[-WEEKLY_WIN:], c[-WEEKLY_WIN:], v[-WEEKLY_WIN:])
        if dpoc is None:
            continue

        zpoc, _, _, znodes = volume_profile(
            h[-ZONE_WIN:], l[-ZONE_WIN:], c[-ZONE_WIN:], v[-ZONE_WIN:])
        supply, demand = zones_from_nodes(znodes, spot, zpoc)

        ad_slope, ad_state = chaikin(h, l, c, v)
        candles = classify_candles(h, l, c, o, v)
        ret20, vol20, strength = momentum_strength(c)

        out["stocks"][sym] = {
            "close": round(spot, 2),
            "poc_daily": round(dpoc, 2),
            "poc_weekly": round(wpoc, 2) if wpoc else None,
            "vah": round(dvah, 2) if dvah else None,
            "val": round(dval, 2) if dval else None,
            "supply": supply,
            "demand": demand,
            "ad_slope": ad_slope,
            "ad_state": ad_state,
            "candles": {k: candles[k] for k in ("blue", "black", "yellow")},
            "ret20": ret20,
            "vol20": vol20,
            "strength": strength,
        }

    out["count"] = len(out["stocks"])
    out["note"] = ("Point of Control, value area and zones are built from DAILY bars, with each "
                   "session's volume placed at its typical price. That is a standard "
                   "volume-by-price approximation, not an intraday profile - treat the levels "
                   "as areas, not exact lines.")
    out["cautions"] = {
        "daily_profile": ("A true POC needs intraday volume at each price. This uses one "
                          "volume point per day, so it is coarser than a tick-level profile."),
        "not_gamma_ray": ("'Gamma Ray' is a proprietary indicator; the momentum and strength "
                          "numbers here are a plain, documented calculation, not a copy of it."),
        "levels_not_support": ("A heavy-volume price is where trading happened, not a promise "
                               "it holds. Zones are areas of interest, not barriers."),
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB  |  %d stocks" % (OUT, os.path.getsize(OUT) / 1024, out["count"]))

    # a few spot checks so the numbers can be eyeballed
    for sym in ("RELIANCE", "TCS", "HDFCBANK"):
        if sym in out["stocks"]:
            s = out["stocks"][sym]
            print("   %-10s close %.2f | POC %.2f (w %.2f) | VA %.2f-%.2f | %s | "
                  "candles %s | 20d %.1f%%"
                  % (sym, s["close"], s["poc_daily"], s["poc_weekly"] or 0,
                     s["val"] or 0, s["vah"] or 0, s["ad_state"], s["candles"], s["ret20"] or 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
