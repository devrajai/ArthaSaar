#!/usr/bin/env python3
"""
build_etf_pages.py - every ETF listed on NSE, with technicals.

The exchange publishes the full ETF list (symbol, underlying, ISIN), which is the
authoritative source - no guessing. Each ETF then gets the same treatment as a stock:
price history from Yahoo, and the technical read from the hub's indicator library.

ETFs are worth tracking separately from stocks because they have no earnings: the
useful comparison is against their own underlying (Nifty, gold, a sector), which is
why the underlying asset is carried through from the exchange file.

Sources (free):
  https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv   the ETF list
  Yahoo Finance                                                          prices

Output: docs/etf.json
  {"updated","count","rows":[...],"pages":{symbol:{...,"series","tech","fund"}}}

Usage:
  python scripts/build_etf_pages.py
  python scripts/build_etf_pages.py --limit 20
"""

from __future__ import annotations

import argparse
import io
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

ETF_LIST = "https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv"
SERIES_LEN = 120
MIN_BARS = 60
CHUNK = 20


def safe(sym: str) -> str:
    return sym.replace("^", "").replace("=", "_").replace(".", "_").replace("-", "_")


def round_or_none(v, nd=2):
    try:
        f = float(v)
        return round(f, nd) if np.isfinite(f) else None
    except Exception:
        return None


def fetch_list(cache: Path) -> pd.DataFrame:
    """The exchange's own ETF list. Cached so a flaky fetch does not empty the page."""
    try:
        import requests
        r = requests.get(ETF_LIST, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and len(r.content) > 500:
            df = pd.read_csv(io.StringIO(r.text))
            df.columns = [c.strip() for c in df.columns]
            cache.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache, index=False)
            print(f"  ETF list: {len(df)} from NSE")
            return df
        print(f"  ETF list: HTTP {r.status_code}, using cache")
    except Exception as e:
        print(f"  ETF list: {type(e).__name__}, using cache")
    if cache.exists():
        df = pd.read_csv(cache)
        df.columns = [c.strip() for c in df.columns]
        print(f"  ETF list: {len(df)} from cache")
        return df
    return pd.DataFrame()


def fetch_history(symbols: list[str], ydir: Path, period: str) -> int:
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance not installed")
        return 0
    ydir.mkdir(parents=True, exist_ok=True)
    missing = [s for s in symbols if not (ydir / f"{safe(s)}.parquet").exists()]
    if not missing:
        return 0
    got = 0
    for i in range(0, len(missing), CHUNK):
        batch = missing[i:i + CHUNK]
        try:
            data = yf.download(batch, period=period, interval="1d", progress=False,
                               auto_adjust=True, group_by="ticker", threads=False)
        except Exception as e:
            print(f"  [warn] batch {i // CHUNK + 1}: {type(e).__name__}")
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
    print(f"  fetched history for {got}/{len(missing)} ETFs")
    return got


def build(sym: str, ydir: Path) -> dict | None:
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
    return {
        "symbol": sym, "close": round(close, 2), "chg_pct": round(chg, 2),
        "series": [round(float(x), 2) for x in d["close"].tail(SERIES_LEN).tolist()],
        "tech": {
            "rsi_14": round_or_none(last.get("rsi_14"), 1), "sma_20": round_or_none(last.get("sma_20")),
            "sma_50": sma50, "sma_200": sma200, "adx": round_or_none(last.get("adx"), 1),
            "atr_pct": round_or_none(last.get("atr_pct"), 2), "macd_hist": round_or_none(last.get("macd_hist"), 3),
            "vol_x": round_or_none(vol_x, 2), "trend": trend,
            "high_52w": round_or_none(d["high"].tail(250).max()),
            "low_52w": round_or_none(d["low"].tail(250).min()),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Every NSE-listed ETF with technicals.")
    ap.add_argument("--out", default="docs/etf.json")
    ap.add_argument("--cache", default="data/nse/etf_list.csv")
    ap.add_argument("--yahoo-dir", default="data/etf")
    ap.add_argument("--period", default="2y")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()

    lst = fetch_list(Path(args.cache))
    if lst.empty:
        print("no ETF list available")
        return 0
    symcol = next((c for c in lst.columns if c.lower() in ("symbol", "symbol ")), None)
    undcol = next((c for c in lst.columns if "underlying asset" in c.lower()), None)
    namecol = next((c for c in lst.columns if "securityname" in c.lower().replace(" ", "")), None)
    if not symcol:
        print(f"no symbol column in {list(lst.columns)}")
        return 0

    rows = []
    for _, r in lst.iterrows():
        sym = str(r[symcol]).strip()
        if not sym or sym.lower() == "nan":
            continue
        rows.append({"symbol": sym, "yahoo": sym + ".NS",
                     "underlying": str(r[undcol]).strip() if undcol else "",
                     "name": str(r[namecol]).strip() if namecol else sym})
    if args.limit:
        rows = rows[:args.limit]
    print(f"ETFs to build: {len(rows)}")

    if not args.no_fetch:
        fetch_history([r["yahoo"] for r in rows], Path(args.yahoo_dir), args.period)

    pages, table = {}, []
    for r in rows:
        rec = build(r["yahoo"], Path(args.yahoo_dir))
        if not rec:
            continue
        rec["symbol"] = r["symbol"]
        rec["name"] = r["name"]
        rec["underlying"] = r["underlying"]
        pages[r["symbol"]] = rec
        t = rec["tech"]
        table.append({"symbol": r["symbol"], "name": r["name"][:34], "underlying": r["underlying"],
                      "close": rec["close"], "chg_pct": rec["chg_pct"], "rsi_14": t["rsi_14"],
                      "trend": t["trend"], "vol_x": t["vol_x"]})

    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "listed": len(rows), "count": len(pages), "series_len": SERIES_LEN,
               "rows": table, "pages": pages}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)")
    print(f"  {len(pages)} of {len(rows)} ETFs with prices and technicals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
