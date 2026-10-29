#!/usr/bin/env python3
"""
build_stock_pages.py - per-stock fundamentals, technicals and chart data.

The NSE universe is ~2,600 symbols. Downloading two years of history for all of them
in one go is hours of requests and gets rate-limited, so this runs in ROTATE mode: each
run deepens a slice of the universe and merges it into the existing file. Coverage
builds up over successive runs instead of nothing being ready until everything is.

Sources (all free):
  prices       local data/yahoo/<symbol>.parquet, else fetched from Yahoo Finance
  technicals   scripts/indicators.py - the verified library the rest of the hub uses
  fundamentals yfinance .info - P/E, P/B, ROE, market cap, dividend yield, beta

Output: docs/stocks.json  (accumulates; never drops a stock it already had)

Usage:
  python scripts/build_stock_pages.py --rotate 300          # deepen 300 not-yet-done
  python scripts/build_stock_pages.py --symbols RELIANCE.NS TCS.NS
  python scripts/build_stock_pages.py --rotate 50 --skip-fundamentals
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
import indicators as ind  # noqa: E402

SERIES_LEN = 120
MIN_BARS = 210
CHUNK = 20          # symbols per yfinance batch download (threads cost memory)


def safe(sym: str) -> str:
    return sym.replace("^", "").replace("=", "_").replace(".", "_").replace("-", "_")


def load_json(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def round_or_none(v, nd=2):
    try:
        f = float(v)
        return round(f, nd) if np.isfinite(f) else None
    except Exception:
        return None


def fundamentals(sym: str) -> dict:
    try:
        import yfinance as yf
        info = yf.Ticker(sym).info or {}
    except Exception:
        return {}
    def g(*keys):
        for k in keys:
            v = info.get(k)
            if v is not None:
                return v
        return None
    return {
        "name": g("longName", "shortName"), "sector": g("sector"), "mcap": g("marketCap"),
        "pe": g("trailingPE"), "pb": g("priceToBook"), "roe": g("returnOnEquity"),
        "eps": g("trailingEps"), "div_yield": g("dividendYield"), "beta": g("beta"),
        "high_52w": g("fiftyTwoWeekHigh"), "low_52w": g("fiftyTwoWeekLow"),
    }


def fetch_history(symbols: list[str], ydir: Path, period: str) -> int:
    """Batch-download any symbol we do not already have on disk. Best effort."""
    missing = [s for s in symbols if not (ydir / f"{safe(s)}.parquet").exists()]
    if not missing:
        return 0
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance not installed - using only what is already on disk")
        return 0
    got = 0
    for i in range(0, len(missing), CHUNK):
        batch = missing[i:i + CHUNK]
        try:
            data = yf.download(batch, period=period, interval="1d", progress=False,
                               auto_adjust=True, group_by="ticker", threads=False)
        except Exception as e:
            print(f"  [warn] batch {i // CHUNK + 1} failed: {type(e).__name__}")
            continue
        for s in batch:
            try:
                d = data[s] if isinstance(data.columns, pd.MultiIndex) else data
                d = d.dropna(subset=["Close"])
                if len(d) < MIN_BARS:
                    continue
                out = pd.DataFrame({
                    "date": pd.to_datetime(d.index).strftime("%Y-%m-%d"),
                    "open": d["Open"].values, "high": d["High"].values,
                    "low": d["Low"].values, "close": d["Close"].values,
                    "volume": d["Volume"].values, "symbol": s,
                })
                out.to_parquet(ydir / f"{safe(s)}.parquet", index=False)
                got += 1
            except Exception:
                continue
        time.sleep(1)
    print(f"  fetched history for {got}/{len(missing)} symbols")
    return got


def build_record(sym: str, ydir: Path, with_fund: bool) -> dict | None:
    p = ydir / f"{safe(sym)}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return None
    if not {"close", "high", "low"}.issubset(df.columns):
        return None
    df = df.sort_values("date").reset_index(drop=True)
    if len(df) < MIN_BARS:
        return None
    try:
        d = ind.add_all(df.copy())
    except Exception:
        return None

    vol_ma = d["volume"].rolling(20).mean()
    vol_x = (d["volume"].iloc[-1] / vol_ma.iloc[-1]) if vol_ma.iloc[-1] else None
    last, prev = d.iloc[-1], d.iloc[-2]
    close = float(last["close"])
    chg = (close / float(prev["close"]) - 1) * 100 if float(prev["close"]) else 0.0

    sma50, sma200 = round_or_none(last.get("sma_50")), round_or_none(last.get("sma_200"))
    if sma50 is not None and sma200 is not None:
        trend = "up" if close > sma50 > sma200 else ("down" if close < sma50 < sma200 else "mixed")
    else:
        trend = "n/a"

    tech = {
        "rsi_14": round_or_none(last.get("rsi_14"), 1), "sma_20": round_or_none(last.get("sma_20")),
        "sma_50": sma50, "sma_200": sma200, "adx": round_or_none(last.get("adx"), 1),
        "atr_pct": round_or_none(last.get("atr_pct"), 2), "macd_hist": round_or_none(last.get("macd_hist"), 3),
        "bb_pctb": round_or_none(last.get("bb_pctb"), 2), "vol_x": round_or_none(vol_x, 2),
        "trend": trend, "high_52w": round_or_none(d["high"].tail(250).max()),
        "low_52w": round_or_none(d["low"].tail(250).min()),
    }
    fund = fundamentals(sym) if with_fund else {}
    return {
        "symbol": sym.replace(".NS", ""), "yahoo": sym,
        "name": fund.get("name") or sym.replace(".NS", ""),
        "sector": fund.get("sector") or "",
        "close": round(close, 2), "chg_pct": round(chg, 2),
        "series": [round(float(x), 2) for x in d["close"].tail(SERIES_LEN).tolist()],
        "tech": tech,
        "fund": {k: (round_or_none(v, 4) if k in ("roe", "div_yield") else round_or_none(v))
                 for k, v in fund.items() if k not in ("name", "sector")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-stock pages (rotate to cover the universe).")
    ap.add_argument("--universe", default="docs/universe.json")
    ap.add_argument("--out", default="docs/stocks.json")
    ap.add_argument("--yahoo-dir", default="data/yahoo")
    ap.add_argument("--rotate", type=int, default=300, help="deepen this many not-yet-done symbols")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--all", action="store_true", help="every symbol in the universe (slow)")
    ap.add_argument("--period", default="2y")
    ap.add_argument("--no-fetch", action="store_true", help="use only local parquet files")
    ap.add_argument("--skip-fundamentals", action="store_true")
    args = ap.parse_args()

    ydir = Path(args.yahoo_dir)
    ydir.mkdir(parents=True, exist_ok=True)
    prev = load_json(args.out) or {"stocks": {}}
    stocks: dict = dict(prev.get("stocks") or {})
    done = {v.get("symbol") for v in stocks.values()}

    # ---- work out which symbols to deepen ----
    if args.symbols:
        targets = args.symbols
    else:
        uni = load_json(args.universe) or {}
        rows = uni.get("rows") or []
        # most liquid first, so the names people actually look for get pages soonest
        rows = [r for r in rows if r.get("volume")]
        rows.sort(key=lambda r: -(r.get("volume") or 0))
        todo = [r["symbol"] + ".NS" for r in rows if r["symbol"] not in done]
        targets = todo if args.all else todo[:args.rotate]
        print(f"universe {uni.get('count', 0)} | already deepened {len(done)} | "
              f"doing {len(targets)} this run | {max(0, len(todo) - len(targets))} left after")

    if not targets:
        print("nothing to do - everything in the universe already has a page")
    else:
        if not args.no_fetch:
            fetch_history(targets, ydir, args.period)

        added = 0
        for i, sym in enumerate(targets, 1):
            rec = build_record(sym, ydir, not args.skip_fundamentals)
            if rec:
                stocks[sym] = rec
                added += 1
            if i % 25 == 0:
                print(f"  {i}/{len(targets)} processed, {added} built")
        print(f"built {added} new pages")

    screener = []
    for k, r in stocks.items():
        t = r.get("tech") or {}
        f = r.get("fund") or {}
        screener.append({
            "symbol": r.get("symbol"), "name": (r.get("name") or "")[:28],
            "sector": r.get("sector") or "", "close": r.get("close"), "chg_pct": r.get("chg_pct"),
            "rsi_14": t.get("rsi_14"), "trend": t.get("trend"), "pe": f.get("pe"),
            "mcap": f.get("mcap"), "div_yield": f.get("div_yield"),
        })
    screener.sort(key=lambda r: -(r.get("mcap") or 0))

    # SPLIT THE SERIES OUT.
    # stocks.json was ~3.1 MB and is loaded on every visit, yet ~1,000 of each stock's ~1,450
    # bytes is the price series, which only the sparkline on the Stocks tab needs. Splitting
    # it means the first paint carries ~500 KB instead of 3.1 MB, and the series arrives only
    # when that tab is opened. Same data, far less paid for by everyone who does not open it.
    series = {}
    lean = {}
    for sym, st in stocks.items():
        ser = st.get("series")
        if ser:
            series[sym] = ser
        st2 = dict(st)
        st2.pop("series", None)
        lean[sym] = st2

    # THE BUG THIS FIXES.
    # This script only builds `--rotate` NEW stocks per run and carries the rest over from
    # the previous stocks.json. Once the series were stripped out of that file, every carried
    # -over stock arrived with no series - so series.json only ever held the handful built
    # that day. It published 9 series for 2,198 stocks, which starved the sparkline and left
    # relative strength ranking 9 names.
    #
    # So fill the gaps from the archive itself, in one query, for every stock still missing
    # one. The archive has all of them; there was never a reason to depend on the carry-over.
    missing = [k for k in stocks if k not in series]
    if missing:
        arch = next((q for q in ("data/candles/daily_adj.parquet",
                                 "data/candles/daily.parquet") if Path(q).exists()), None)
        if arch:
            try:
                import duckdb
                con = duckdb.connect()
                con.execute("SET threads=1")
                con.execute("SET memory_limit='1200MB'")
                want = [m.replace(".NS", "").replace(".BO", "") for m in missing]
                rows = con.execute("""
                  WITH r AS (
                    SELECT symbol, close,
                           row_number() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
                    FROM read_parquet(?)
                    WHERE close > 0 AND symbol IN (SELECT * FROM unnest(?))
                  )
                  SELECT symbol, close FROM r WHERE rn <= ? ORDER BY symbol, rn DESC
                """, [arch, want, SERIES_LEN]).fetchall()
                con.close()
                by_sym = {}
                for sym, close in rows:
                    by_sym.setdefault(sym, []).append(round(float(close), 2))
                filled = 0
                for m in missing:
                    key = m.replace(".NS", "").replace(".BO", "")
                    if by_sym.get(key):
                        series[m] = by_sym[key]
                        filled += 1
                print(f"  series filled from the archive: {filled} of {len(missing)} missing")
            except Exception as e:
                print(f"  series backfill failed ({type(e).__name__}): {str(e)[:90]}")
        else:
            print("  series backfill skipped - no archive on disk")

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(stocks), "series_len": SERIES_LEN,
        "series_file": "series.json",
        "screener": screener, "stocks": lean,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(stocks)} stocks total")

    series_dest = dest.parent / "series.json"
    series_dest.write_text(json.dumps(
        {"updated": payload["updated"], "series": series}, separators=(",", ":")))
    print(f"Wrote {series_dest}  ({series_dest.stat().st_size / 1e3:.0f} KB)  |  "
          f"{len(series)} price series (loaded on the Stocks tab only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
