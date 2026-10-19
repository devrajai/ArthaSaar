#!/usr/bin/env python3
"""
fetch_crypto.py - collect crypto OHLCV history.

Two free sources, tried in order:
  1. Binance public REST (no key, no signup, deep history)   - primary
  2. Yahoo Finance via yfinance                                - fallback

Binance is preferred for crypto: it is the exchange's own data, has years of history,
and needs no key. Yahoo is the safety net (it is also what the rest of the hub uses).

Both are unofficial/unlicensed for redistribution - fine for research and backtesting,
not for execution or resale.

Usage
-----
  python scripts/fetch_crypto.py                          # all pairs in the config
  python scripts/fetch_crypto.py --source yahoo
  python scripts/fetch_crypto.py --symbols BTCUSDT ETHUSDT --interval 1d --limit 1000

Output: data/crypto/<pair>.parquet  and  data/crypto/_all.parquet
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

BINANCE = "https://api.binance.com/api/v3/klines"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}

# If Binance is unreachable once, stop retrying it for every pair - otherwise a
# blocked/slow network turns into one long timeout per pair.
_BINANCE_DOWN = False


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def from_binance(symbol: str, interval: str, limit: int) -> pd.DataFrame | None:
    """Paginate Binance klines (max 1000 per call)."""
    rows, end = [], None
    remaining = limit
    while remaining > 0:
        take = min(1000, remaining)
        url = f"{BINANCE}?symbol={symbol}&interval={interval}&limit={take}"
        if end:
            url += f"&endTime={end}"
        global _BINANCE_DOWN
        try:
            req = urllib.request.Request(url, headers=UA)
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        except Exception as e:  # noqa: BLE001
            print(f"    binance error: {type(e).__name__}: {str(e)[:60]}")
            _BINANCE_DOWN = True
            return None
        if not data:
            break
        rows = data + rows
        end = data[0][0] - 1
        remaining -= len(data)
        if len(data) < take:
            break
        time.sleep(0.25)
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_base", "taker_quote", "ignore"])
    for c in ("open", "high", "low", "close", "volume", "quote_volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    df["symbol"] = symbol
    df["source"] = "binance"
    return df[["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume", "source"]]


def from_yahoo(yahoo_symbol: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf
        df = yf.download(yahoo_symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df["symbol"] = yahoo_symbol
        df["source"] = "yahoo"
        keep = ["symbol", "date", "open", "high", "low", "close", "volume", "source"]
        for c in keep:
            if c not in df.columns:
                df[c] = pd.NA
        return df[keep]
    except ImportError:
        print("    yahoo error: yfinance not installed (pip install yfinance)")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"    yahoo error: {type(e).__name__}: {str(e)[:60]}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect crypto OHLCV (Binance, Yahoo fallback).")
    ap.add_argument("--config", default="config/crypto_symbols.json")
    ap.add_argument("--source", default="auto", choices=["auto", "binance", "yahoo"])
    ap.add_argument("--symbols", nargs="*", default=None, help="Binance symbols (overrides config)")
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--limit", type=int, default=1000, help="max Binance candles per pair")
    ap.add_argument("--period", default="5y", help="Yahoo period when falling back")
    ap.add_argument("--out", default="data/crypto")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text()) if Path(args.config).exists() else {"pairs": []}
    pairs = cfg.get("pairs", [])
    if args.symbols:
        pairs = [{"name": s, "binance": s, "yahoo": s.replace("USDT", "-USD")} for s in args.symbols]
    if not pairs:
        raise SystemExit("no pairs to fetch")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"crypto: {len(pairs)} pair(s), source={args.source}, interval={args.interval}")

    frames = []
    for p in pairs:
        name, bsym, ysym = p.get("name", "?"), p.get("binance"), p.get("yahoo")
        df = None
        if args.source == "binance" or (args.source == "auto" and not _BINANCE_DOWN):
            if bsym:
                df = from_binance(bsym, args.interval, args.limit)
        if df is None and args.source in ("auto", "yahoo") and ysym:
            print(f"  {name}: falling back to Yahoo ({ysym})")
            df = from_yahoo(ysym, args.period, args.interval)
        if df is None or df.empty:
            print(f"  {name}: FAILED both sources")
            continue
        df.to_parquet(out / f"{_safe(bsym or ysym)}.parquet", index=False)
        frames.append(df)
        print(f"  {name}: {len(df)} rows ({df['source'].iloc[0]}), {df['date'].min()} -> {df['date'].max()}")

    if frames:
        allf = pd.concat(frames, ignore_index=True)
        allf.to_parquet(out / "_all.parquet", index=False)
        print(f"\nWrote {len(frames)} pair(s) + _all.parquet  |  {len(allf):,} rows")
    else:
        print("nothing fetched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
