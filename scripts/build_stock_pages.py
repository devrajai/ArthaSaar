#!/usr/bin/env python3
"""
build_stock_pages.py - per-stock fundamentals, technicals and chart data.

For every symbol in the `nse_stocks` group it produces one compact record the website
turns into a stock page: a price series to draw, the technical picture, and the
fundamentals. Output is a single JSON so the static site makes one request.

Sources (all free):
  prices       data/yahoo/<symbol>.parquet  (Yahoo Finance, written by fetch_yahoo.py)
  technicals   scripts/indicators.py - the same verified library the rest of the hub uses
  fundamentals yfinance .info (Yahoo) - P/E, P/B, ROE, market cap, dividend yield, beta

Output: docs/stocks.json
  {
    "updated": "...", "count": 60, "series_len": 120,
    "screener": [ {symbol,name,sector,close,chg_pct,rsi_14,trend,pe,mcap,div_yield}, ... ],
    "stocks": { "RELIANCE.NS": {..., "series": [...], "tech": {...}, "fund": {...}}, ... }
  }

Usage:
  python scripts/build_stock_pages.py
  python scripts/build_stock_pages.py --skip-fundamentals    # prices+technicals only
  python scripts/build_stock_pages.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
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

SERIES_LEN = 120          # trading days drawn on the chart
MIN_BARS = 210            # need 200-day SMA plus a little room


def safe(sym: str) -> str:
    return sym.replace("^", "").replace("=", "_").replace(".", "_").replace("-", "_")


def load_config(path: str) -> list[str]:
    try:
        c = json.loads(Path(path).read_text())
        return list(c.get("groups", {}).get("nse_stocks", []))
    except Exception:
        return []


def fundamentals(sym: str) -> dict:
    """Yahoo fundamentals. Slow and best-effort - never fatal."""
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
        "name": g("longName", "shortName"),
        "sector": g("sector"),
        "mcap": g("marketCap"),
        "pe": g("trailingPE"),
        "pb": g("priceToBook"),
        "roe": g("returnOnEquity"),
        "eps": g("trailingEps"),
        "div_yield": g("dividendYield"),
        "beta": g("beta"),
        "high_52w": g("fiftyTwoWeekHigh"),
        "low_52w": g("fiftyTwoWeekLow"),
    }


def round_or_none(v, nd=2):
    try:
        f = float(v)
        return round(f, nd) if np.isfinite(f) else None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-stock fundamentals + technicals + chart data.")
    ap.add_argument("--config", default="config/yahoo_symbols.json")
    ap.add_argument("--yahoo-dir", default="data/yahoo")
    ap.add_argument("--out", default="docs/stocks.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-fundamentals", action="store_true")
    args = ap.parse_args()

    syms = load_config(args.config)
    if args.limit:
        syms = syms[:args.limit]
    if not syms:
        print("no symbols in config - nothing to do")
        return 0

    ydir = Path(args.yahoo_dir)
    stocks: dict[str, dict] = {}
    screener: list[dict] = []
    skipped = 0

    for i, sym in enumerate(syms, 1):
        p = ydir / f"{safe(sym)}.parquet"
        if not p.exists():
            skipped += 1
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            skipped += 1
            continue
        if not {"close", "high", "low"}.issubset(df.columns):
            skipped += 1
            continue
        df = df.sort_values("date").reset_index(drop=True)
        if len(df) < MIN_BARS:
            skipped += 1
            continue

        try:
            d = ind.add_all(df.copy())
        except Exception as e:
            print(f"  [warn] {sym}: indicators failed ({type(e).__name__})")
            skipped += 1
            continue

        # volume versus its own 20-day average (add_all() does not expose this)
        vol_ma = d["volume"].rolling(20).mean()
        vol_x = (d["volume"].iloc[-1] / vol_ma.iloc[-1]) if vol_ma.iloc[-1] else None

        last = d.iloc[-1]
        prev = d.iloc[-2]
        close = float(last["close"])
        chg = (close / float(prev["close"]) - 1) * 100 if float(prev["close"]) else 0.0

        # trend read from the moving averages, the way a person would
        sma50, sma200 = round_or_none(last.get("sma_50")), round_or_none(last.get("sma_200"))
        if sma50 is not None and sma200 is not None:
            trend = "up" if close > sma50 > sma200 else ("down" if close < sma50 < sma200 else "mixed")
        else:
            trend = "n/a"

        tech = {
            "rsi_14": round_or_none(last.get("rsi_14"), 1),
            "sma_20": round_or_none(last.get("sma_20")),
            "sma_50": sma50,
            "sma_200": sma200,
            "adx": round_or_none(last.get("adx"), 1),
            "atr_pct": round_or_none(last.get("atr_pct"), 2),
            "macd_hist": round_or_none(last.get("macd_hist"), 3),
            "bb_pctb": round_or_none(last.get("bb_pctb"), 2),
            "vol_x": round_or_none(vol_x, 2),
            "trend": trend,
            "high_52w": round_or_none(d["high"].tail(250).max()),
            "low_52w": round_or_none(d["low"].tail(250).min()),
        }

        fund = {} if args.skip_fundamentals else fundamentals(sym)

        series = [round(float(x), 2) for x in d["close"].tail(SERIES_LEN).tolist()]
        rec = {
            "symbol": sym.replace(".NS", ""),
            "yahoo": sym,
            "name": fund.get("name") or sym.replace(".NS", ""),
            "sector": fund.get("sector") or "",
            "close": round(close, 2),
            "chg_pct": round(chg, 2),
            "series": series,
            "tech": tech,
            "fund": {k: (round_or_none(v, 4) if k in ("roe", "div_yield") else round_or_none(v))
                     for k, v in fund.items() if k not in ("name", "sector")},
        }
        stocks[sym] = rec
        screener.append({
            "symbol": rec["symbol"], "name": rec["name"][:28], "sector": rec["sector"],
            "close": rec["close"], "chg_pct": rec["chg_pct"],
            "rsi_14": tech["rsi_14"], "trend": trend,
            "pe": rec["fund"].get("pe"), "mcap": rec["fund"].get("mcap"),
            "div_yield": rec["fund"].get("div_yield"),
        })
        if i % 10 == 0:
            print(f"  {i}/{len(syms)} ...")

    screener.sort(key=lambda r: -(r.get("mcap") or 0))
    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(stocks),
        "series_len": SERIES_LEN,
        "screener": screener,
        "stocks": stocks,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)")
    print(f"  {len(stocks)} stocks with a page, {skipped} skipped (no data or < {MIN_BARS} bars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
