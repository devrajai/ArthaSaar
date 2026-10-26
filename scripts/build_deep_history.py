#!/usr/bin/env python3
"""Deep-history analytics: everything that becomes possible once you have 8 years of prices.

All of it is DERIVED - nothing here collects new data. Input is the candle archive; output
is a handful of SMALL summary JSONs, because the repo must not grow (the raw history lives
on Drive and stays there).

WHAT IT PUBLISHES
  docs/report_cards.json   per stock: yearly returns, worst drop, volatility, best/worst
                           month, beta vs Nifty, years up out of the last 7
  docs/market_stats.json   index level: current drawdown vs past falls, volatility cone,
                           day-of-week effect, streak stats, SIP heatmap

CAUTIONS, ALL ENFORCED IN CODE
  * SURVIVORSHIP BIAS - the archive holds only symbols listed TODAY. Every delisted,
    merged or suspended company is missing, so historical returns look better than they
    really were. The output carries the warning so the page can show it.
  * SPLITS AND BONUSES - prices must be adjusted. This reads whatever the archive holds;
    the pipeline's corporate-action step runs BEFORE this, so the input is already adjusted.
    The output records which file it read.
  * SMALL SAMPLES - any bucket with fewer than MIN_SAMPLE observations is dropped rather
    than published. A 60% hit rate on 3 observations is noise, not an edge.
"""
import json, os, sys
from datetime import datetime, timezone

MIN_SAMPLE = 20          # below this, hide the result entirely
BENCH_SYMBOL = "NIFTYBEES"   # Nifty 50 ETF, present for all 1,928 days in the archive
OUT_RC = "docs/report_cards.json"
OUT_MS = "docs/market_stats.json"


def _con():
    import duckdb
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1200MB'")
    con.execute("SET preserve_insertion_order=false")
    return con




def _xirr(cfs, lo=-0.95, hi=3.0, iters=200):
    """Money-weighted annual return for irregular cash flows [(period, amount)].

    Bisection on NPV. Negative = money out (each SIP instalment), positive = final value.
    Returns None if it does not converge, rather than inventing a number.
    """
    def npv(r):
        return sum(a / ((1.0 + r) ** (t / 12.0)) for t, a in cfs)
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-6:
            return mid
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def prepare(con, arch):
    """Build an ADJUSTED price table `px`, and report what it had to correct.

    WHY THIS EXISTS - it is not optional. NIFTYBEES drops 89.9% on 2019-12-19 in the raw
    archive: that is a 1:10 split, not a crash. Left unadjusted it made the index look
    80% down when it was actually 126% UP, and every split stock shows the same fake
    collapse. NSE's price bands make a genuine one-day move beyond about 20% almost
    impossible, so a move that lands on a simple split ratio is a corporate action.

    Adjustment: for each date, multiply by every split factor that happens AFTER it, so
    the series becomes continuous and the newest price stays the real one.
    """
    con.execute("""
      CREATE OR REPLACE TEMP TABLE splits AS
      WITH r AS (
        SELECT symbol, date, close,
               close / lag(close) OVER (PARTITION BY symbol ORDER BY date) AS ratio
        FROM read_parquet(?)
      )
      SELECT symbol, date, ratio AS factor FROM r
      WHERE ratio IS NOT NULL AND (
           (ratio BETWEEN 0.45 AND 0.55) OR (ratio BETWEEN 0.30 AND 0.36)
        OR (ratio BETWEEN 0.22 AND 0.27) OR (ratio BETWEEN 0.17 AND 0.21)
        OR (ratio BETWEEN 0.08 AND 0.11) OR (ratio BETWEEN 1.90 AND 2.10)
        OR (ratio BETWEEN 2.80 AND 3.20) OR (ratio BETWEEN 9.00 AND 11.00))
    """, [arch])
    nsym, nspl = con.execute("SELECT count(DISTINCT symbol), count(*) FROM splits").fetchone()

    con.execute("""
      CREATE OR REPLACE TEMP TABLE px AS
      WITH base AS (
        SELECT a.symbol, a.date, a.open, a.high, a.low, a.close, a.volume,
               coalesce(s.factor, 1.0) AS f
        FROM read_parquet(?) a
        LEFT JOIN splits s ON s.symbol = a.symbol AND s.date = a.date
      ), k AS (
        SELECT symbol, date, open, high, low, close, volume,
               coalesce(exp(sum(ln(f)) OVER (PARTITION BY symbol ORDER BY date DESC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)), 1.0) AS k
        FROM base
      )
      SELECT symbol, date, open*k AS open, high*k AS high, low*k AS low,
             close*k AS close, volume/k AS volume FROM k
    """, [arch])
    print("  split-adjusted: %d corporate actions across %d symbols" % (nspl, nsym))
    return nspl, nsym


def find_archive():
    for p in ("data/candles/cm_daily.parquet", "data/candles/daily.parquet"):
        if os.path.exists(p):
            return p
    return None


def q1(con, sql, params=None):
    r = con.execute(sql, params or []).fetchone()
    return r


# =====================================================================================
#  PER-STOCK REPORT CARDS
# =====================================================================================
def report_cards(con, arch, bench_ret):
    """One row per stock: the things a person actually asks about a stock."""
    # daily returns for every symbol
    con.execute("""
      CREATE OR REPLACE TEMP TABLE ret AS
      SELECT symbol, date, close,
             close / lag(close) OVER (PARTITION BY symbol ORDER BY date) - 1.0 AS r
      FROM px
      WHERE close IS NOT NULL AND close > 0
    """)

    # yearly returns: last close of the year vs last close of the previous year
    con.execute("""
      CREATE OR REPLACE TEMP TABLE yr AS
      WITH yl AS (
        SELECT symbol, substr(date,1,4) AS y,
               arg_max(close, date) AS last_close
        FROM px WHERE close > 0 GROUP BY 1,2
      )
      SELECT symbol, y, last_close,
             lag(last_close) OVER (PARTITION BY symbol ORDER BY y) AS prev_close
      FROM yl
    """)
    years = con.execute("""
      SELECT symbol, y, last_close/prev_close - 1.0 AS ret
      FROM yr WHERE prev_close IS NOT NULL AND prev_close > 0
    """).fetchall()

    per_year = {}
    for sym, y, r in years:
        per_year.setdefault(sym, {})[int(y)] = round(float(r), 4)

    # volatility, max drawdown, worst single day - BATCHED BY SYMBOL.
    # A single running-max window across 3.5M rows exhausts memory, so we walk the symbol
    # list in chunks and accumulate. Same answer, bounded memory.
    all_syms = [r[0] for r in con.execute("SELECT DISTINCT symbol FROM px ORDER BY symbol").fetchall()]
    stats = []
    B = 350
    for i in range(0, len(all_syms), B):
        chunk = all_syms[i:i + B]
        ph = ",".join("?" * len(chunk))
        rows = con.execute("""
          WITH d AS (
            SELECT symbol, date, close, volume,
                   max(close) OVER (PARTITION BY symbol ORDER BY date
                                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS peak
            FROM px WHERE close > 0 AND symbol IN (%s)
          )
          SELECT symbol,
                 stddev_samp(r) * sqrt(252)      AS vol,
                 min(close/peak - 1.0)           AS mdd,
                 min(r)                          AS worst_day,
                 count(*)                        AS n
          FROM (SELECT symbol, date, close, peak, volume,
                       close/lag(close) OVER (PARTITION BY symbol ORDER BY date) - 1.0 AS r
                FROM d)
          GROUP BY 1 HAVING count(*) >= ?
        """ % ph, chunk + [MIN_SAMPLE]).fetchall()
        stats.extend(rows)
    print("    volatility/drawdown for %d symbols (in %d batches)" % (len(stats), (len(all_syms)+B-1)//B))
    # span per symbol, computed separately - DuckDB refuses to nest aggregates inside
    # datediff(), and this is a trivial extra query rather than a fight with the planner
    spans = {sym: (a, b) for sym, a, b in
             con.execute("SELECT symbol, min(date), max(date) FROM px GROUP BY 1").fetchall()}
    import datetime as _dt
    def coverage(sym, n):
        a, b = spans.get(sym, (None, None))
        if not a or not b:
            return 0.0
        try:
            days = (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days
        except ValueError:
            return 0.0
        expected = days * 252.0 / 365.0
        return (n / expected) if expected > 0 else 0.0

    by_sym = {s: {"vol": v, "mdd": m, "worst_day": w, "n": n, "coverage": coverage(s, n)}
              for s, v, m, w, n in stats}

    # best and worst calendar month, from monthly compounded returns
    months = []
    for i in range(0, len(all_syms), B):
        chunk = all_syms[i:i + B]
        ph = ",".join("?" * len(chunk))
        months.extend(con.execute("""
          WITH ml AS (
            SELECT symbol, substr(date,1,7) AS ym, arg_max(close,date) AS c
            FROM px WHERE close > 0 AND symbol IN (%s) GROUP BY 1,2
          ), mr AS (
            SELECT symbol, ym, c/lag(c) OVER (PARTITION BY symbol ORDER BY ym) - 1.0 AS r
            FROM ml
          )
          SELECT symbol, ym, r FROM mr WHERE r IS NOT NULL
        """ % ph, chunk).fetchall())
    month_best, month_worst = {}, {}
    for sym, ym, r in months:
        b = month_best.get(sym)
        w = month_worst.get(sym)
        if b is None or r > b[1]:
            month_best[sym] = (ym, float(r))
        if w is None or r < w[1]:
            month_worst[sym] = (ym, float(r))

    # ---- beta against the benchmark -------------------------------------------
    # cov(stock, market) / var(market), joined on date so both see the same sessions.
    # Done in SQL: a python loop over 3,510 symbols would mean 3,510 passes.
    betas = {}
    rows = con.execute("""
      WITH b AS (
        SELECT date, close/lag(close) OVER (ORDER BY date) - 1.0 AS r
        FROM px WHERE symbol = ? AND close > 0
      ), s AS (
        SELECT symbol, date, r FROM ret WHERE r IS NOT NULL
      )
      SELECT s.symbol,
             covar_pop(s.r, b.r) / nullif(var_pop(b.r), 0) AS beta,
             count(*) AS n
      FROM s JOIN b USING(date)
      GROUP BY 1 HAVING count(*) >= ?
    """, [BENCH_SYMBOL, MIN_SAMPLE]).fetchall()
    for sym, beta, n in rows:
        if beta is not None:
            betas[sym] = float(beta)
    print("    betas computed for %d symbols" % len(betas))

    out = []
    for sym, st in by_sym.items():
        yrs = per_year.get(sym, {})
        up = sum(1 for y, r in yrs.items() if y >= 2019 and r > 0)
        total_years = len([y for y in yrs if y >= 2019])
        b = betas.get(sym)
        rec = {
            "symbol": sym,
            "vol_pct": round(st["vol"] * 100, 1) if st["vol"] is not None else None,
            "max_drawdown_pct": round(st["mdd"] * 100, 1) if st["mdd"] is not None else None,
            "worst_day_pct": round(st["worst_day"] * 100, 1) if st["worst_day"] is not None else None,
            "days": st["n"],
            "coverage": st.get("coverage"),   # used by the gate below, then dropped
            "years_up": up,
            "years_total": total_years,
            "yearly": {str(y): v for y, v in sorted(yrs.items())},
        }
        if sym in month_best:
            rec["best_month"] = {"month": month_best[sym][0],
                                 "ret_pct": round(month_best[sym][1] * 100, 1)}
        if sym in month_worst:
            rec["worst_month"] = {"month": month_worst[sym][0],
                                  "ret_pct": round(month_worst[sym][1] * 100, 1)}
        if b is not None:
            rec["beta"] = round(b, 2)
        out.append(rec)

    # REPO SIZE (caution #4): publish a summary, not a dump. A stock needs at least a
    # year of sessions for any of these figures to mean anything, and nulls are dropped
    # rather than serialised. The full history stays on Drive.
    # COVERAGE GATE. A stock with long gaps has multi-month "daily" returns, which makes
    # beta and drawdown arithmetic rather than information - DIACABS had a 12-month hole
    # and a +3118% jump, giving beta -15.4. Requiring the series to cover 85% of the
    # sessions between its first and last date removes that class of nonsense.
    out = [r for r in out
           if (r.get("days") or 0) >= 250 and (r.get("coverage") or 0) >= 0.85]
    for r in out:
        r.pop("coverage", None)
    for r in out:
        r.pop("days", None)
        for k in ("vol_pct", "max_drawdown_pct", "worst_day_pct"):
            if r.get(k) is None:
                r.pop(k, None)
    out.sort(key=lambda x: -(x.get("years_up") or 0))
    return out


# =====================================================================================
#  INDEX-LEVEL STATS
# =====================================================================================
def market_stats(con, arch):
    ms = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "benchmark": BENCH_SYMBOL, "note": "", "cautions": {}}

    bench = con.execute("""
      SELECT date, close FROM px
      WHERE symbol = ? AND close > 0 ORDER BY date
    """, [BENCH_SYMBOL]).fetchall()
    if len(bench) < MIN_SAMPLE:
        ms["note"] = "Benchmark series too short to analyse."
        return ms
    dates = [d for d, _ in bench]
    closes = [float(c) for _, c in bench]
    ms["span"] = [dates[0], dates[-1]]
    ms["days"] = len(dates)

    # ---- drawdown: now vs the past, and how long recovery took --------------------
    peak = closes[0]; peak_i = 0
    mdd = 0.0; episodes = []; cur = None
    for i, c in enumerate(closes):
        if c > peak:
            if cur:
                cur["recovered_on"] = dates[i]
                cur["recovery_days"] = i - cur["trough_i"]
                episodes.append(cur); cur = None
            peak = c; peak_i = i
        dd = c / peak - 1.0
        if dd < mdd:
            mdd = dd
        if dd <= -0.10 and cur is None:
            cur = {"peak_on": dates[peak_i], "peak": round(peak, 2),
                   "trough_i": i, "trough_on": dates[i], "trough": round(c, 2),
                   "depth_pct": round(dd * 100, 1)}
        elif cur and dd < cur["depth_pct"] / 100:
            cur["trough_i"] = i; cur["trough_on"] = dates[i]
            cur["trough"] = round(c, 2); cur["depth_pct"] = round(dd * 100, 1)
    if cur:
        cur["recovered_on"] = None; cur["recovery_days"] = None
        episodes.append(cur)

    ath = max(closes)
    ms["drawdown"] = {
        "now_pct": round((closes[-1] / ath - 1.0) * 100, 2),
        "all_time_high": round(ath, 2),
        "worst_ever_pct": round(mdd * 100, 1),
        "episodes": [e for e in episodes if e["depth_pct"] <= -10][:8],
    }

    # ---- volatility cone: today's 20-day realised vol vs its own history ----------
    import statistics as st
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    def rv(w):
        return [st.stdev(rets[i - w:i]) * (252 ** 0.5) for i in range(w, len(rets) + 1)]
    cone = {}
    for w in (20, 60, 120):
        series = rv(w)
        if len(series) < MIN_SAMPLE:
            continue
        series_sorted = sorted(series)
        now = series[-1]
        pct = sum(1 for v in series if v < now) / len(series) * 100
        cone["%dd" % w] = {
            "now_pct": round(now * 100, 1),
            "percentile": round(pct),
            "p10": round(series_sorted[int(0.10 * len(series))] * 100, 1),
            "p50": round(series_sorted[int(0.50 * len(series))] * 100, 1),
            "p90": round(series_sorted[int(0.90 * len(series))] * 100, 1),
            "samples": len(series),
        }
    ms["vol_cone"] = cone

    # ---- day-of-week effect ------------------------------------------------------
    import datetime as dt
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    buckets = {n: [] for n in dow_names}
    for i in range(1, len(dates)):
        try:
            d = dt.date.fromisoformat(dates[i])
        except ValueError:
            continue
        if d.weekday() > 4:
            continue
        buckets[dow_names[d.weekday()]].append(rets[i - 1])
    dow = {}
    for n, vals in buckets.items():
        if len(vals) < MIN_SAMPLE:
            continue
        dow[n] = {"avg_pct": round(sum(vals) / len(vals) * 100, 3),
                  "up_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100),
                  "n": len(vals)}
    ms["day_of_week"] = dow

    # ---- streak stats: what happens after N consecutive down days ----------------
    def after_streak(k):
        out = {1: [], 5: [], 20: []}
        run = 0
        for i in range(len(rets)):
            if rets[i] < 0:
                run += 1
            else:
                run = 0
            if run == k:
                for h in out:
                    j = i + h
                    if j < len(rets):
                        out[h].append(sum(rets[i + 1:j + 1]))
        return {h: {"avg_pct": round(sum(v) / len(v) * 100, 2),
                    "up_pct": round(sum(1 for x in v if x > 0) / len(v) * 100),
                    "n": len(v)} for h, v in out.items() if len(v) >= MIN_SAMPLE}

    def after_high():
        """What happens after a fresh 52-week high."""
        out = {1: [], 5: [], 20: []}
        look = 252
        for i in range(look, len(closes)):
            if closes[i] >= max(closes[i - look:i + 1]):
                for h in out:
                    j = i + h
                    if j < len(rets):
                        out[h].append(sum(rets[i:j]))
        return {h: {"avg_pct": round(sum(v) / len(v) * 100, 2),
                    "up_pct": round(sum(1 for x in v if x > 0) / len(v) * 100),
                    "n": len(v)} for h, v in out.items() if len(v) >= MIN_SAMPLE}

    ms["streaks"] = {
        "after_3_down_days": after_streak(3),
        "after_5_down_days": after_streak(5),
        "after_52w_high": after_high(),
    }

    # ---- rolling SIP heatmap: start month -> CAGR to today -----------------------
    # a SIP buys a fixed rupee amount on the first trading day of every month
    import collections
    by_month = collections.OrderedDict()
    for d, c in zip(dates, closes):
        by_month.setdefault(d[:7], []).append(c)
    months = [(m, v[0]) for m, v in by_month.items()]
    sip = {}
    for start in range(len(months)):
        amt = 0.0; units = 0.0
        for m, price in months[start:]:
            amt += 1000.0
            units += 1000.0 / price
        if amt <= 0:
            continue
        final = units * closes[-1]
        n = len(months) - start
        if n <= 0:
            continue
        # XIRR, not CAGR. A SIP is not a lump sum: money goes in monthly, so
        # final/invested ^ (1/years) badly understates the return - it treats every rupee
        # as if it had been invested on day one. XIRR solves for the rate that makes the
        # discounted cash flows net to zero, which is the honest number.
        # XIRR only where it means something. Annualising a 2-month SIP produces figures
        # like -50%, which are arithmetically right and useless to a reader. Below a year
        # we publish the total return and leave the rate out.
        xirr = _xirr([(i, -1000.0) for i in range(n)] + [(n - 1, final)]) if n >= 12 else None
        sip[months[start][0]] = {
            "invested": round(amt), "value": round(final),
            "xirr_pct": round(xirr * 100, 1) if xirr is not None else None,
            "total_ret_pct": round((final / amt - 1) * 100, 1),
            "months": n}
    ms["sip_heatmap"] = sip

    ms["cautions"] = {
        "survivorship": ("This archive contains only stocks listed on NSE TODAY. Companies "
                         "that were delisted, merged or suspended are absent, so past "
                         "returns here look better than they really were. Treat every "
                         "historical figure as an upper bound."),
        "adjusted": "Prices are corporate-action adjusted by the pipeline before this runs.",
        "min_sample": ("Any bucket with fewer than %d observations is hidden rather than "
                       "published." % MIN_SAMPLE),
    }
    ms["note"] = ("Computed from %s over %d sessions. The benchmark is the Nifty 50 ETF "
                  "(NIFTYBEES), which tracks the index and is present for every session."
                  % (BENCH_SYMBOL, len(dates)))
    return ms


def main():
    arch = find_archive()
    if not arch:
        print("no candle archive found - run candles_from_drive.py first")
        return 1
    print("archive:", arch)
    con = _con()
    n = q1(con, "SELECT count(*) FROM read_parquet(?)", [arch])[0]
    print("rows:", f"{n:,}")
    print("\npreparing prices ...")
    prepare(con, arch)

    print("\nbuilding market stats ...")
    ms = market_stats(con, arch)
    print("  drawdown now: %s%%  | worst ever: %s%%"
          % (ms.get("drawdown", {}).get("now_pct"), ms.get("drawdown", {}).get("worst_ever_pct")))
    for k, v in (ms.get("vol_cone") or {}).items():
        print("  vol cone %-4s now %s%% (percentile %s)" % (k, v["now_pct"], v["percentile"]))
    print("  day-of-week buckets:", list((ms.get("day_of_week") or {}).keys()))
    print("  sip months:", len(ms.get("sip_heatmap") or {}))

    print("\nbuilding report cards ...")
    rcs = report_cards(con, arch, None)
    print("  stocks:", len(rcs))

    os.makedirs("docs", exist_ok=True)
    json.dump({"updated": ms["updated"], "benchmark": BENCH_SYMBOL,
               "note": ms["note"], "cautions": ms["cautions"], "cards": rcs},
              open(OUT_RC, "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(ms, open(OUT_MS, "w"), ensure_ascii=False)
    for p in (OUT_RC, OUT_MS):
        print("-> %s  %.1f KB" % (p, os.path.getsize(p) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
