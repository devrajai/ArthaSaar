#!/usr/bin/env python3
"""Correlation - which stocks move together, and which sectors do.

WHY THIS WAS REWRITTEN
The old version read the ~500-point series out of docs/stocks.json and kept the 40 stocks
with the most observations over a fixed 60 sessions. That was all it could do with the data
it had. Now there are 8 years of split-adjusted candles on disk, so:

  * the universe is the Nifty 500 rather than "whatever had the longest series"
  * there are TWO windows, 1 year and 3 years, because correlation is not stable - a pair
    that moves together over three years can decouple completely inside one
  * sectors get their own matrix, which is the more useful question for a portfolio

SIZE. A 500x500 matrix is 250,000 numbers - far too big to publish. So the full universe is
used to find the most correlated PAIRS, while the published matrix is a readable 60x60.
Breadth without a multi-megabyte file.

A CORRELATION IS NOT A CAUSE. Two stocks correlate because they share a driver - a sector, a
commodity, an index weight. It is also unstable: it rises in a crash, when everything falls
together, and that is exactly when a "diversified" portfolio turns out not to be.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/correlation.json"
UNIVERSE = 500        # how many stocks to consider
MATRIX_N = 60         # how many go into the published matrix
PAIRS_N = 40          # how many top pairs to publish
MIN_OBS = 120         # a year of sessions; below this a correlation is noise


def find_archive():
    for p in ("data/candles/daily_adj.parquet", "data/candles/daily.parquet"):
        if os.path.exists(p):
            return p
    return None


def _con():
    import duckdb
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1400MB'")
    con.execute("SET preserve_insertion_order=false")
    return con


def cutoff_date(arch, sessions):
    """Calendar date `sessions` trading days back. ~1.46 calendar days per session."""
    con = _con()
    row = con.execute("SELECT max(date) FROM read_parquet(?)", [arch]).fetchone()
    con.close()
    if not row or not row[0]:
        return None
    import datetime as dt
    last = dt.date.fromisoformat(str(row[0])[:10])
    return (last - dt.timedelta(days=int(sessions * 1.46))).isoformat()


def turnover():
    """{symbol: close*volume} from the universe file - a liquidity proxy.

    Ordering the matrix by completeness put KSOLVES and PSPPROJECT at the top, because old
    illiquid stocks have the longest history. That is not what anyone wants to look at. Rank
    by traded value instead, so the 60 published names are the ones people actually hold.
    """
    try:
        u = json.load(open("docs/universe.json"))
    except Exception:
        return {}
    out = {}
    for r in (u.get("rows") or []):
        sym = str(r.get("symbol") or "").upper()
        try:
            tv = float(r.get("close") or 0) * float(r.get("volume") or 0)
        except Exception:
            tv = 0.0
        if sym:
            out[sym] = tv
    return out


def real_equities():
    """Symbols that are actual shares, not ETF wrappers.

    Without this the universe filled up with ETFs - BANKBEES, BANKIETF, CASHIETF - because
    they have complete history. They correlate at 0.99 with each other by construction (same
    index, different wrapper), so they crowded out every interesting pair in the list. The
    universe file carries series == 'EQ' for real equities only.
    """
    try:
        u = json.load(open("docs/universe.json"))
    except Exception:
        return None
    out = set()
    for r in (u.get("rows") or []):
        sym = str(r.get("symbol") or "").upper()
        if sym and str(r.get("series") or "EQ").upper() == "EQ":
            out.add(sym)
    return out or None


def pick_universe(arch, sessions, n):
    """The n most-complete symbols inside the window.

    Uses a DATE CUTOFF rather than row_number() OVER (PARTITION BY symbol). The window
    function needs a full sort of 3.5M rows and blew the memory limit; filtering by date
    first makes the same selection cheap.
    """
    cut = cutoff_date(arch, sessions)
    if not cut:
        return []
    con = _con()
    rows = con.execute("""
      SELECT symbol, count(*) AS n FROM read_parquet(?)
      WHERE close > 0 AND date >= ?
      GROUP BY 1 HAVING count(*) >= ? ORDER BY n DESC
    """, [arch, cut, MIN_OBS]).fetchall()
    con.close()
    eq = real_equities()
    tv = turnover()
    picked = []
    for sym, cnt in rows:
        if eq is not None and sym not in eq:
            continue
        picked.append((sym, cnt))
        if len(picked) >= n:
            break
    # the 500 are chosen by completeness (they must have enough history to correlate at all);
    # the published 60 are then the most heavily traded of those.
    picked.sort(key=lambda x: -(tv.get(x[0], 0.0)))
    return [s for s, _c in picked]


def load_returns(arch, sessions, symbols):
    """Wide frame of daily returns for the given symbols only."""
    if not symbols:
        return None
    cut = cutoff_date(arch, sessions)
    con = _con()
    ph = ",".join("?" * len(symbols))
    df = con.execute("""
      SELECT symbol, date,
             close / lag(close) OVER (PARTITION BY symbol ORDER BY date) - 1.0 AS ret
      FROM read_parquet(?)
      WHERE close > 0 AND date >= ? AND symbol IN (%s)
      QUALIFY ret IS NOT NULL
    """ % ph, [arch, cut] + list(symbols)).fetchdf()
    con.close()
    if df.empty:
        return None
    wide = df.pivot(index="date", columns="symbol", values="ret")
    del df
    return wide


def sector_of():
    try:
        secs = json.load(open("docs/sectors.json"))
    except Exception:
        return {}
    out = {}
    for s in (secs.get("sectors") or []):
        nm = s.get("name")
        for st in (s.get("stocks") or []):
            sym = str(st.get("symbol") or "").upper()
            if sym:
                out[sym] = nm
    return out


def sector_returns(wide, mapping):
    """Average the constituents of each sector, then correlate the sector series."""
    groups = {}
    for sym in wide.columns:
        sec = mapping.get(sym)
        if sec:
            groups.setdefault(sec, []).append(sym)
    out = {}
    for sec, syms in groups.items():
        if len(syms) >= 3:
            out[sec] = wide[syms].mean(axis=1)
    if not out:
        return None
    import pandas as pd
    return pd.DataFrame(out)


def matrix_block(frame, limit=None):
    if frame is None or frame.shape[1] < 2:
        return None
    cols = list(frame.columns)[:limit] if limit else list(frame.columns)
    c = frame[cols].corr(min_periods=MIN_OBS // 2).round(3)
    return {"symbols": cols,
            "matrix": [[None if v != v else v for v in row] for row in c.values.tolist()]}


def top_pairs(frame, n):
    """The most correlated pairs across the WHOLE universe, not just the published matrix."""
    c = frame.corr(min_periods=MIN_OBS // 2)
    cols = list(c.columns)
    seen = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = c.iat[i, j]
            if v == v:                       # skip NaN
                seen.append((float(v), cols[i], cols[j]))
    seen.sort(reverse=True)
    return [{"a": a, "b": b, "corr": round(v, 3)} for v, a, b in seen[:n]]


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "note": "", "cautions": {}}

    arch = find_archive()
    if not arch:
        out["note"] = "No candle archive on disk, so no correlation is published."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("correlation: skipped (no archive)")
        return 0

    try:
        import pandas as pd  # noqa
    except Exception:
        out["note"] = "pandas unavailable."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 1

    print("archive:", arch)
    windows = {}
    for label, sessions in (("1y", 250), ("3y", 750)):
        keep = pick_universe(arch, sessions, UNIVERSE)
        if len(keep) < 2:
            print("  %s: not enough stocks with history" % label)
            continue
        wide = load_returns(arch, sessions, keep)
        if wide is None or wide.shape[1] < 2:
            print("  %s: not enough data" % label)
            continue
        # pivot() sorts columns alphabetically, which made the published 60x60 matrix an
        # arbitrary alphabetical slice - 20MICRONS, 3MINDIA, 3PLAND. Reindex to `keep`, which
        # is ordered by completeness, so the matrix shows the 60 most-covered stocks.
        wide = wide[[c for c in keep if c in wide.columns]]
        print("  %s: %d stocks x %d sessions" % (label, len(keep), wide.shape[0]))
        block = {"stocks": matrix_block(wide, MATRIX_N),
                 "pairs": top_pairs(wide, PAIRS_N),
                 "universe": len(keep),
                 "sessions": int(wide.shape[0])}
        windows[label] = block
        if label == "1y":
            sec = sector_returns(wide, sector_of())
            if sec is not None:
                block["sectors"] = matrix_block(sec)
                print("    sectors: %d" % (sec.shape[1] if sec is not None else 0))

    if not windows:
        out["note"] = "Not enough history to correlate anything yet."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 0

    # keep the old flat shape working too: symbols/matrix/count from the 1y block
    one = windows.get("1y") or windows.get("3y")
    out["symbols"] = (one.get("stocks") or {}).get("symbols") or []
    out["matrix"] = (one.get("stocks") or {}).get("matrix") or []
    out["count"] = len(out["symbols"])
    out["windows"] = windows
    out["note"] = ("Correlation of daily returns over 1 year and 3 years, across up to %d "
                   "stocks. The matrix shows the %d largest; the pair list covers all of "
                   "them." % (one.get("universe", 0), MATRIX_N))
    out["cautions"] = {
        "not_cause": ("Correlation means two things share a driver, not that one moves the "
                      "other."),
        "unstable": ("It is not stable. Correlations rise in a sell-off, when everything "
                     "falls together - which is exactly when diversification is supposed to "
                     "help and does not."),
        "survivorship": ("The universe is stocks listed today, so dead companies are absent."),
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for label, b in windows.items():
        print("   %s: %d stocks, %d pairs" % (label, b.get("universe", 0), len(b.get("pairs") or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
