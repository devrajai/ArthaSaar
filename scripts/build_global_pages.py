#!/usr/bin/env python3
"""
build_global_pages.py - global stocks by country: technicals, fundamentals, and the
country's index.

Same idea as the NSE pages, but grouped by country so the site can offer a country
filter. Each country carries its benchmark index, so you can see a stock against the
market it actually trades in rather than against the S&P.

Sources (free): Yahoo Finance - daily candles and company data.

Output: docs/global.json
  {"updated": "...", "countries": 14, "stocks": 180,
   "index": [ {country, symbol, name, close, chg_pct, rsi_14, trend} ... ],   # the benchmarks
   "rows":  [ {country, symbol, name, close, chg_pct, rsi_14, trend, pe, mcap, div_yield} ],
   "pages": { "AAPL": {..., "series": [...], "tech": {...}, "fund": {...}, "country": "..."} } }

Usage:
  python scripts/build_global_pages.py
  python scripts/build_global_pages.py --countries "United States" Japan
  python scripts/build_global_pages.py --skip-fundamentals
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
CHUNK = 20


def safe(sym: str) -> str:
    return sym.replace("^", "").replace("=", "_").replace(".", "_").replace("-", "_")


def round_or_none(v, nd=2):
    try:
        f = float(v)
        return round(f, nd) if np.isfinite(f) else None
    except Exception:
        return None


def load_config(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text()).get("countries", {})
    except Exception:
        return {}


def fetch(symbols: list[str], ydir: Path, period: str) -> int:
    missing = [s for s in symbols if not (ydir / f"{safe(s)}.parquet").exists()]
    if not missing:
        return 0
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance not installed - using cached files only")
        return 0
    got = 0
    for i in range(0, len(missing), CHUNK):
        batch = missing[i:i + CHUNK]
        try:
            data = yf.download(batch, period=period, interval="1d", progress=False,
                               auto_adjust=True, group_by="ticker", threads=False)
        except Exception as e:
            print(f"  [warn] batch failed: {type(e).__name__}")
            continue
        for s in batch:
            try:
                d = data[s] if isinstance(data.columns, pd.MultiIndex) else data
                d = d.dropna(subset=["Close"])
                if len(d) < MIN_BARS:
                    continue
                pd.DataFrame({
                    "date": pd.to_datetime(d.index).strftime("%Y-%m-%d"),
                    "open": d["Open"].values, "high": d["High"].values,
                    "low": d["Low"].values, "close": d["Close"].values,
                    "volume": d["Volume"].values, "symbol": s,
                }).to_parquet(ydir / f"{safe(s)}.parquet", index=False)
                got += 1
            except Exception:
                continue
        time.sleep(1)
    print(f"  fetched {got}/{len(missing)}")
    return got


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
    return {"name": g("longName", "shortName"), "sector": g("sector"), "mcap": g("marketCap"),
            "pe": g("trailingPE"), "pb": g("priceToBook"), "roe": g("returnOnEquity"),
            "eps": g("trailingEps"), "div_yield": g("dividendYield"), "beta": g("beta"),
            "high_52w": g("fiftyTwoWeekHigh"), "low_52w": g("fiftyTwoWeekLow")}


def build(sym: str, ydir: Path, with_fund: bool) -> dict | None:
    p = ydir / f"{safe(sym)}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p).sort_values("date").reset_index(drop=True)
    except Exception:
        return None
    if len(df) < MIN_BARS or not {"close", "high", "low"}.issubset(df.columns):
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
    trend = ("up" if close > sma50 > sma200 else "down" if close < sma50 < sma200 else "mixed") \
        if (sma50 is not None and sma200 is not None) else "n/a"
    fund = fundamentals(sym) if with_fund else {}
    return {
        "symbol": sym, "name": fund.get("name") or sym, "sector": fund.get("sector") or "",
        "close": round(close, 2), "chg_pct": round(chg, 2),
        "series": [round(float(x), 2) for x in d["close"].tail(SERIES_LEN).tolist()],
        "tech": {"rsi_14": round_or_none(last.get("rsi_14"), 1), "sma_20": round_or_none(last.get("sma_20")),
                 "sma_50": sma50, "sma_200": sma200, "adx": round_or_none(last.get("adx"), 1),
                 "atr_pct": round_or_none(last.get("atr_pct"), 2), "macd_hist": round_or_none(last.get("macd_hist"), 3),
                 "vol_x": round_or_none(vol_x, 2), "trend": trend,
                 "high_52w": round_or_none(d["high"].tail(250).max()),
                 "low_52w": round_or_none(d["low"].tail(250).min())},
        "fund": {k: (round_or_none(v, 4) if k in ("roe", "div_yield") else round_or_none(v))
                 for k, v in fund.items() if k not in ("name", "sector")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Global stock pages, grouped by country.")
    ap.add_argument("--config", default="config/universe_global.json")
    ap.add_argument("--yahoo-dir", default="data/yahoo")
    ap.add_argument("--out", default="docs/global.json")
    ap.add_argument("--countries", nargs="*", default=None)
    ap.add_argument("--period", default="2y")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--skip-fundamentals", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.countries:
        cfg = {k: v for k, v in cfg.items() if k in args.countries}
    if not cfg:
        print("no countries configured")
        return 0

    ydir = Path(args.yahoo_dir)
    ydir.mkdir(parents=True, exist_ok=True)

    all_syms = [s for c in cfg.values() for s in c.get("symbols", [])]
    idx_syms = [c.get("index") for c in cfg.values() if c.get("index")]
    print(f"countries: {len(cfg)} | stocks: {len(all_syms)} | indices: {len(idx_syms)}")
    if not args.no_fetch:
        fetch(sorted(set(all_syms + idx_syms)), ydir, args.period)

    pages, rows = {}, []
    for country, c in cfg.items():
        for sym in c.get("symbols", []):
            rec = build(sym, ydir, not args.skip_fundamentals)
            if not rec:
                continue
            rec["country"] = country
            pages[sym] = rec
            t, f = rec["tech"], rec["fund"]
            rows.append({"country": country, "symbol": sym, "name": (rec["name"] or "")[:26],
                         "close": rec["close"], "chg_pct": rec["chg_pct"], "rsi_14": t["rsi_14"],
                         "trend": t["trend"], "pe": f.get("pe"), "mcap": f.get("mcap"),
                         "div_yield": f.get("div_yield")})
        print(f"  {country}: {sum(1 for r in rows if r['country'] == country)} stocks")

    # country benchmarks
    index_rows = []
    for country, c in cfg.items():
        isym = c.get("index")
        if not isym:
            continue
        rec = build(isym, ydir, False)
        if rec:
            index_rows.append({"country": country, "symbol": isym, "name": rec["name"],
                               "close": rec["close"], "chg_pct": rec["chg_pct"],
                               "rsi_14": rec["tech"]["rsi_14"], "trend": rec["tech"]["trend"]})

    rows.sort(key=lambda r: -(r.get("mcap") or 0))
    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "countries": sorted({r["country"] for r in rows}),
        "stocks": len(pages), "series_len": SERIES_LEN,
        "index": index_rows, "rows": rows, "pages": pages,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(pages)} stocks, "
          f"{len(index_rows)} country indices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
