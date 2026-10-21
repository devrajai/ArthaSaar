#!/usr/bin/env python3
"""
build_crypto_pages.py - per-coin pages for crypto: chart, technicals, market data.

Crypto trades 24/7 and there are hundreds of pairs, so this mirrors the stock pages:
a list ranked by traded volume, and a page per coin with a chart and the same
technical read (RSI, moving averages, ADX, ATR, volume multiple).

Sources (free, no API key):
  Binance public REST  /api/v3/ticker/24hr  - every pair, sorted by quote volume
                       /api/v3/klines       - daily candles
  Yahoo Finance        <COIN>-USD           - fallback price history and market cap

Note on "fundamentals": a coin has no earnings, so P/E and ROE do not exist. What is
meaningful is supply, market cap and volume - so those are what the page shows.

Output: docs/crypto.json
  {"updated": "...", "count": 120, "series_len": 120,
   "rows": [ {symbol,base,quote,close,chg_pct,volume,quote_volume,trades,rsi_14,trend,atr_pct} ],
   "coins": { "BTCUSDT": {..., "series": [...], "tech": {...}, "market": {...}} } }

Usage:
  python scripts/build_crypto_pages.py --top 120
  python scripts/build_crypto_pages.py --top 20 --no-fetch      # offline, uses cache
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
MIN_BARS = 60          # crypto has no 200-day requirement for a useful read
API = "https://api.binance.com"


def round_or_none(v, nd=2):
    try:
        f = float(v)
        return round(f, nd) if np.isfinite(f) else None
    except Exception:
        return None


def get_json(url: str, params: dict | None = None, tries: int = 3):
    import requests
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30,
                             headers={"User-Agent": "ArthaSaar/1.0"})
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = f"{type(e).__name__}"
        time.sleep(2 * (i + 1))
    print(f"    [warn] {url.split('/')[-1]}: {last}")
    return None


def top_pairs(top: int) -> list[dict]:
    """Every USDT pair, ranked by 24h quote volume."""
    data = get_json(f"{API}/api/v3/ticker/24hr")
    if not isinstance(data, list):
        return []
    rows = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        if any(x in sym for x in ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")):
            continue  # leveraged tokens, not coins
        try:
            qv = float(t.get("quoteVolume") or 0)
        except Exception:
            continue
        if qv <= 0:
            continue
        rows.append({
            "symbol": sym, "base": sym[:-4], "quote": "USDT",
            "close": round_or_none(t.get("lastPrice"), 6),
            "chg_pct": round_or_none(t.get("priceChangePercent")),
            "volume": round_or_none(t.get("volume")),
            "quote_volume": round_or_none(qv),
            "trades": int(float(t.get("count") or 0)),
            "high_24h": round_or_none(t.get("highPrice"), 6),
            "low_24h": round_or_none(t.get("lowPrice"), 6),
        })
    rows.sort(key=lambda r: -(r["quote_volume"] or 0))
    return rows[:top]


def klines(symbol: str, limit: int = 500) -> pd.DataFrame:
    data = get_json(f"{API}/api/v3/klines",
                    {"symbol": symbol, "interval": "1d", "limit": limit})
    if not isinstance(data, list) or len(data) < MIN_BARS:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_base", "taker_quote", "ignore"])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.strftime("%Y-%m-%d")
    return df[["date", "open", "high", "low", "close", "volume"]].dropna()


def record(pair: dict, df: pd.DataFrame) -> dict | None:
    if df.empty:
        return None
    try:
        d = ind.add_all(df.copy())
    except Exception:
        return None
    vol_ma = d["volume"].rolling(20).mean()
    vol_x = (d["volume"].iloc[-1] / vol_ma.iloc[-1]) if vol_ma.iloc[-1] else None
    last = d.iloc[-1]
    close = float(last["close"])
    sma50, sma200 = round_or_none(last.get("sma_50")), round_or_none(last.get("sma_200"))
    if sma50 is not None and sma200 is not None:
        trend = "up" if close > sma50 > sma200 else ("down" if close < sma50 < sma200 else "mixed")
    else:
        trend = "n/a"
    tech = {
        "rsi_14": round_or_none(last.get("rsi_14"), 1), "sma_20": round_or_none(last.get("sma_20"), 6),
        "sma_50": sma50, "sma_200": sma200, "adx": round_or_none(last.get("adx"), 1),
        "atr_pct": round_or_none(last.get("atr_pct"), 2), "macd_hist": round_or_none(last.get("macd_hist"), 6),
        "vol_x": round_or_none(vol_x, 2), "trend": trend,
        "high_52w": round_or_none(d["high"].tail(365).max(), 6),
        "low_52w": round_or_none(d["low"].tail(365).min(), 6),
    }
    return {
        "symbol": pair["symbol"], "base": pair["base"], "quote": pair["quote"],
        "close": pair.get("close"), "chg_pct": pair.get("chg_pct"),
        "series": [round(float(x), 6) for x in d["close"].tail(SERIES_LEN).tolist()],
        "tech": tech,
        "market": {k: pair.get(k) for k in
                   ("volume", "quote_volume", "trades", "high_24h", "low_24h")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Crypto pages (list + per-coin technicals).")
    ap.add_argument("--top", type=int, default=120)
    ap.add_argument("--out", default="docs/crypto.json")
    ap.add_argument("--cache", default="data/crypto/klines")
    ap.add_argument("--no-fetch", action="store_true", help="use only cached klines")
    args = ap.parse_args()

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    pairs = top_pairs(args.top) if not args.no_fetch else []
    if not pairs:
        # offline: fall back to whatever klines we have cached
        pairs = [{"symbol": p.stem, "base": p.stem.replace("USDT", ""), "quote": "USDT",
                  "close": None, "chg_pct": None} for p in sorted(cache.glob("*.csv"))]
        if not pairs:
            print("no pairs (Binance unreachable and no cache) - nothing to do")
            return 0
    print(f"pairs: {len(pairs)}")

    coins, rows = {}, []
    for i, pair in enumerate(pairs, 1):
        sym = pair["symbol"]
        cp = cache / f"{sym}.csv"
        df = pd.DataFrame()
        if cp.exists():
            try:
                df = pd.read_csv(cp)
            except Exception:
                df = pd.DataFrame()
        if df.empty and not args.no_fetch:
            df = klines(sym)
            if not df.empty:
                df.to_csv(cp, index=False)
        if df.empty:
            continue
        rec = record(pair, df)
        if not rec:
            continue
        coins[sym] = rec
        t = rec["tech"]
        rows.append({**{k: pair.get(k) for k in ("symbol", "base", "close", "chg_pct",
                                                 "quote_volume", "trades")},
                     "rsi_14": t["rsi_14"], "trend": t["trend"], "atr_pct": t["atr_pct"]})
        if i % 20 == 0:
            print(f"  {i}/{len(pairs)} ...")

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(coins), "series_len": SERIES_LEN,
        "rows": rows, "coins": coins,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(coins)} coins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
