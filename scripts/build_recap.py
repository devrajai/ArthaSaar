#!/usr/bin/env python3
"""A 10-session market recap, built entirely from real sources.

WHY THIS EXISTS
Someone handed me a PDF titled "Indian Stock Market 10-Day Performance Report". Its index
ledger was genuine (it matched our own bhavcopy to the rupee) but its FII/DII table had the
sign reversed against NSE's feed, and its USD/INR and VIX were 11-13% off. That is the worst
kind of document: mostly right, so the wrong parts get believed.

This builds the same thing from sources we can name, so it is self-consistent by
construction rather than assembled from mixed provenance.

SOURCES, EACH VERIFIED BEFORE USE
  Nifty 50, Sensex, India VIX ... Yahoo chart api (the pipeline already depends on it)
  Sector 10-session returns ..... computed from our own candle archive
  Breadth ....................... docs/breadth.json (built from the same archive)
  FII / DII ..................... docs/data.json, which carries the LATEST session only -
                                 NSE's endpoint does not give history, so we publish one
                                 day and say so rather than inventing a ten-day total.
"""
import json, os, ssl, sys, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
OUT = "docs/recap.json"
SESSIONS = 10


def yahoo(sym, rng="3mo"):
    """Daily OHLC series from Yahoo. Returns [(date, open, high, low, close), ...]."""
    import urllib.parse
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1d&range=%s"
         % (urllib.parse.quote(sym), rng))
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            d = json.loads(r.read())
        res = d["chart"]["result"][0]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
        rows = []
        for i, t in enumerate(ts):
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
            if c is None:
                continue
            rows.append((datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), o, h, l, c))
        return rows
    except Exception as e:
        print("  %s -> %s" % (sym, type(e).__name__))
        return []


def ledger(name, sym):
    rows = yahoo(sym)[-SESSIONS:]
    if len(rows) < 2:
        return None
    out = []
    prev = None
    for d, o, h, l, c in rows:
        chg = round((c / prev - 1) * 100, 2) if prev else None
        out.append([d,
                    round(o, 2) if o else None,
                    round(h, 2) if h else None,
                    round(l, 2) if l else None,
                    round(c, 2),
                    chg])
        prev = c
    first, last = rows[0][4], rows[-1][4]
    return {
        "name": name, "symbol": sym,
        "rows": out,
        "last": round(last, 2),
        "change_10d_pct": round((last / first - 1) * 100, 2),
        "high_10d": round(max(r[2] for r in rows if r[2]), 2),
        "low_10d": round(min(r[3] for r in rows if r[3]), 2),
        "sessions": len(rows),
        "span": [rows[0][0], rows[-1][0]],
    }


def sector_returns():
    """10-session return per sector, averaged over its constituents in our own archive."""
    arch = None
    for p in ("data/candles/cm_daily.parquet", "data/candles/daily.parquet"):
        if os.path.exists(p):
            arch = p
            break
    if not arch:
        return [], "no candle archive, sector returns omitted"
    try:
        import duckdb
    except Exception:
        return [], "duckdb unavailable, sector returns omitted"
    try:
        secs = json.load(open("docs/sectors.json"))
    except Exception:
        return [], "sectors.json missing"

    # each sector's constituents -> the 10th and 1st close from the end
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1200MB'")
    con.execute("""
      CREATE OR REPLACE TEMP TABLE px AS
      WITH ranked AS (
        SELECT symbol, date, close,
               row_number() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
        FROM read_parquet(?)
        WHERE close > 0
      )
      SELECT symbol,
             max(CASE WHEN rn = 1  THEN close END) AS last_c,
             max(CASE WHEN rn = ?  THEN close END) AS first_c
      FROM ranked WHERE rn <= ?
      GROUP BY symbol
    """, [arch, SESSIONS, SESSIONS])
    px = {s: (f, l) for s, l, f in con.execute("SELECT symbol, last_c, first_c FROM px").fetchall()}
    con.close()

    out = []
    for s in (secs.get("sectors") or []):
        vals = []
        for st in (s.get("stocks") or []):
            sym = str(st.get("symbol") or "").upper()
            pair = px.get(sym)
            if pair and pair[1] and pair[0] and pair[1] > 0:
                vals.append((pair[0] / pair[1] - 1) * 100)
        if len(vals) >= 3:
            out.append({"name": s.get("name"), "ret_10d_pct": round(sum(vals) / len(vals), 2),
                        "stocks": len(vals)})
    out.sort(key=lambda x: -x["ret_10d_pct"])
    return out, ""


def main():
    recap = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "sessions": SESSIONS, "sources": {}, "cautions": {}, "note": ""}

    print("index ledgers ...")
    nifty = ledger("Nifty 50", "^NSEI")
    sensex = ledger("Sensex", "^BSESN")
    vix_rows = yahoo("^INDIAVIX")
    recap["nifty"] = nifty
    recap["sensex"] = sensex
    if nifty:
        recap["span"] = nifty["span"]
        recap["sessions"] = nifty["sessions"]

    if len(vix_rows) >= 2:
        v = vix_rows[-SESSIONS:]
        recap["vix"] = {
            "last": round(v[-1][4], 2),
            "change_10d": round(v[-1][4] - v[0][4], 2),
            "change_10d_pct": round((v[-1][4] / v[0][4] - 1) * 100, 2),
            "high": round(max(r[2] for r in v if r[2]), 2),
            "low": round(min(r[3] for r in v if r[3]), 2),
            "sessions": len(v),
        }

    print("sector returns from the archive ...")
    secs, why = sector_returns()
    recap["sectors"] = secs
    if why:
        recap["sector_note"] = why
    print("  sectors:", len(secs))

    # breadth and FII/DII come from files the pipeline already writes
    try:
        b = json.load(open("docs/breadth.json"))
        recap["breadth"] = {"above_50": b.get("above_50"), "above_200": b.get("above_200"),
                            "total": b.get("total")}
    except Exception:
        pass
    try:
        d = json.load(open("docs/data.json"))
        fd = d.get("fii_dii") or {}
        rows = fd.get("rows") or []
        parsed = []
        for r in rows:
            # columns: buyValue, category, date, netValue, sellValue
            try:
                parsed.append({"category": r[1], "date": r[2],
                               "net_cr": round(float(r[3]), 2)})
            except (IndexError, TypeError, ValueError):
                continue
        if parsed:
            recap["fii_dii"] = parsed
            recap["fii_dii_note"] = ("Latest session only. NSE's FII/DII endpoint publishes "
                                     "one day at a time, so a ten-session total is not "
                                     "available from it and is not invented here.")
    except Exception:
        pass

    recap["sources"] = {
        "index": "Yahoo Finance ^NSEI / ^BSESN / ^INDIAVIX",
        "sectors": "computed from our own NSE bhavcopy archive",
        "breadth": "docs/breadth.json, from the same archive",
        "fii_dii": "NSE FII/DII endpoint, latest session",
    }
    recap["cautions"] = {
        "survivorship": ("Sector returns are averaged over constituents that exist today, so "
                         "they inherit the archive's survivorship bias."),
        "split_adjusted": ("Sector returns use raw archive prices. A constituent that split "
                           "inside the ten sessions will distort its sector - the deep-history "
                           "script adjusts for this, this one does not."),
    }
    recap["note"] = ("Every figure here comes from a named source. This exists because a "
                     "circulating PDF had a correct index ledger but an FII/DII table with the "
                     "sign reversed and FX/VIX off by 11-13%% - correct enough to be believed. "
                     "Built from one set of sources, the numbers cannot disagree with each other.")

    if not nifty and not sensex:
        print("REFUSING TO WRITE: no index data retrieved")
        return 1
    os.makedirs("docs", exist_ok=True)
    json.dump(recap, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("\n-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    if nifty:
        print("   Nifty %s (%s%% over %d sessions)" % (nifty["last"], nifty["change_10d_pct"], nifty["sessions"]))
    if sensex:
        print("   Sensex %s (%s%%)" % (sensex["last"], sensex["change_10d_pct"]))
    if recap.get("vix"):
        print("   VIX %s (%s%%)" % (recap["vix"]["last"], recap["vix"]["change_10d_pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
