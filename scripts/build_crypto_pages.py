#!/usr/bin/env python3
"""
build_crypto_pages.py - per-coin pages for crypto: chart, technicals, market data.

WHY YAHOO IS THE PRIMARY SOURCE
  Binance geo-blocks US IP addresses, and GitHub Actions runners are in the US - so a
  Binance-only build silently produces nothing in CI. Yahoo's <COIN>-USD feed works
  from both a normal runner and a restricted container, so it drives the build.
  Binance and CoinGecko are used only to enrich (real 24h volume, market cap) when
  they happen to be reachable.

  Verified: from this sandbox only Yahoo answered; Binance, CoinGecko, Kraken and
  Coinbase all failed. That is exactly the case this ordering survives.

Output: docs/crypto.json
  {"updated","count","rows":[...],"coins":{"BTC":{"symbol","name","series","tech","market"}}}

Usage:
  python scripts/build_crypto_pages.py --top 100
  python scripts/build_crypto_pages.py --top 20 --period 1y
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
MIN_BARS = 60
CHUNK = 20
BINANCE = "https://api.binance.com"
GECKO = "https://api.coingecko.com/api/v3"


def round_or_none(v, nd=2):
    try:
        f = float(v)
        return round(f, nd) if np.isfinite(f) else None
    except Exception:
        return None


def load_coins(path: str, top: int) -> list[dict]:
    try:
        cfg = json.loads(Path(path).read_text())
        coins = cfg.get("coins") or []
    except Exception:
        coins = []
    return coins[:top] if top else coins


def try_json(url: str, params: dict | None = None, timeout: int = 15):
    """Best-effort JSON. Returns None on anything at all - these are enrichments."""
    try:
        import requests
        r = requests.get(url, params=params, timeout=timeout,
                         headers={"User-Agent": "ArthaSaar/1.0"})
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def gecko_markets() -> dict:
    """Market cap / rank / 24h volume from CoinGecko, if it answers."""
    data = try_json(f"{GECKO}/coins/markets",
                    {"vs_currency": "usd", "order": "market_cap_desc",
                     "per_page": 250, "page": 1})
    if not isinstance(data, list):
        return {}
    out = {}
    for c in data:
        sym = str(c.get("symbol") or "").upper()
        if not sym:
            continue
        out[sym] = {"rank": c.get("market_cap_rank"), "mcap": c.get("market_cap"),
                    "volume_24h": c.get("total_volume"), "name": c.get("name"),
                    "ath": c.get("ath"), "supply": c.get("circulating_supply")}
    return out


def binance_24h() -> dict:
    """Real 24h stats from Binance, if it answers."""
    data = try_json(f"{BINANCE}/api/v3/ticker/24hr")
    if not isinstance(data, list):
        return {}
    out = {}
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        out[sym[:-4]] = {"volume_24h": round_or_none(t.get("quoteVolume")),
                         "trades": int(float(t.get("count") or 0)),
                         "high_24h": round_or_none(t.get("highPrice"), 6),
                         "low_24h": round_or_none(t.get("lowPrice"), 6),
                         "chg_24h": round_or_none(t.get("priceChangePercent"))}
    return out


def fetch_history(coins: list[dict], ydir: Path, period: str) -> int:
    """Daily history from Yahoo, in batches."""
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance not installed - nothing to fetch")
        return 0
    ydir.mkdir(parents=True, exist_ok=True)
    tickers = [c["yahoo"] for c in coins]
    missing = [t for t in tickers if not (ydir / (t.replace("-", "_") + ".parquet")).exists()]
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
        for t in batch:
            try:
                d = data[t] if isinstance(data.columns, pd.MultiIndex) else data
                d = d.dropna(subset=["Close"])
                if len(d) < MIN_BARS:
                    continue
                pd.DataFrame({
                    "date": pd.to_datetime(d.index).strftime("%Y-%m-%d"),
                    "open": d["Open"].values, "high": d["High"].values,
                    "low": d["Low"].values, "close": d["Close"].values,
                    "volume": d["Volume"].values,
                }).to_parquet(ydir / (t.replace("-", "_") + ".parquet"), index=False)
                got += 1
            except Exception:
                continue
        time.sleep(1)
    print(f"  fetched history for {got}/{len(missing)} coins")
    return got


def build_coin(coin: dict, ydir: Path, gecko: dict, binance: dict) -> dict | None:
    t = coin["yahoo"]
    p = ydir / (t.replace("-", "_") + ".parquet")
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p).sort_values("date").reset_index(drop=True)
    except Exception:
        return None
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
    sma50, sma200 = round_or_none(last.get("sma_50"), 6), round_or_none(last.get("sma_200"), 6)
    trend = ("up" if close > sma50 > sma200 else "down" if close < sma50 < sma200 else "mixed") \
        if (sma50 is not None and sma200 is not None) else "n/a"

    base = coin["symbol"]
    g = gecko.get(base, {})
    b = binance.get(base, {})
    return {
        "symbol": base, "name": g.get("name") or coin.get("name") or base,
        "yahoo": t, "close": round(close, 6), "chg_pct": round(chg, 2),
        "series": [round(float(x), 6) for x in d["close"].tail(SERIES_LEN).tolist()],
        "tech": {
            "rsi_14": round_or_none(last.get("rsi_14"), 1), "sma_20": round_or_none(last.get("sma_20"), 6),
            "sma_50": sma50, "sma_200": sma200, "adx": round_or_none(last.get("adx"), 1),
            "atr_pct": round_or_none(last.get("atr_pct"), 2),
            "macd_hist": round_or_none(last.get("macd_hist"), 6), "vol_x": round_or_none(vol_x, 2),
            "trend": trend, "high_52w": round_or_none(d["high"].tail(365).max(), 6),
            "low_52w": round_or_none(d["low"].tail(365).min(), 6),
        },
        "market": {
            "rank": g.get("rank"), "mcap": g.get("mcap"),
            "volume_24h": b.get("volume_24h") or g.get("volume_24h"),
            "trades": b.get("trades"), "high_24h": b.get("high_24h"), "low_24h": b.get("low_24h"),
            "ath": g.get("ath"), "supply": g.get("supply"),
            "volume_source": "Binance" if b else ("CoinGecko" if g else "Yahoo"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Crypto pages (list + per-coin technicals).")
    ap.add_argument("--config", default="config/crypto_symbols.json")
    ap.add_argument("--yahoo-dir", default="data/crypto/yahoo")
    ap.add_argument("--out", default="docs/crypto.json")
    ap.add_argument("--top", type=int, default=250, help="how many coins to build (0 = all CoinGecko returns)")
    ap.add_argument("--period", default="2y")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()

    coins = load_coins(args.config, 0) or []
    cfg_names = {c["symbol"]: c.get("name") for c in coins}
    print(f"coins configured: {len(coins)}")

    # CoinGecko ranks every listed coin by market cap, so use it as the universe when
    # it is reachable - that is what makes this "all listed" rather than a hand list.
    gecko_list = gecko_markets()
    if gecko_list:
        ranked = sorted(gecko_list.items(), key=lambda kv: (kv[1].get("rank") or 10 ** 9))
        want = args.top if args.top else 250
        from_list = []
        for sym, info in ranked[:want]:
            if not sym.isalnum():
                continue
            from_list.append({"symbol": sym, "name": info.get("name") or cfg_names.get(sym) or sym,
                              "yahoo": sym + "-USD"})
        if len(from_list) > len(coins):
            print(f"  CoinGecko universe: {len(from_list)} coins (supersedes the config list)")
            coins = from_list
    if not coins:
        print(f"no coins available (config empty and CoinGecko unreachable)")
        return 0
    if args.top:
        coins = coins[:args.top]
    print(f"coins to build: {len(coins)}")

    ydir = Path(args.yahoo_dir)
    if not args.no_fetch:
        fetch_history(coins, ydir, args.period)

    gecko = gecko_list
    print(f"  CoinGecko enrichment: {len(gecko)} coins" if gecko else "  CoinGecko: unreachable (fine)")
    bnc = binance_24h()
    print(f"  Binance enrichment : {len(bnc)} pairs" if bnc else "  Binance: unreachable (fine)")

    built, rows = {}, []
    for c in coins:
        rec = build_coin(c, ydir, gecko, bnc)
        if not rec:
            continue
        built[rec["symbol"]] = rec
        t, m = rec["tech"], rec["market"]
        rows.append({"symbol": rec["symbol"], "base": rec["symbol"], "name": rec["name"],
                     "close": rec["close"], "chg_pct": rec["chg_pct"], "rsi_14": t["rsi_14"],
                     "trend": t["trend"], "atr_pct": t["atr_pct"],
                     "mcap": m.get("mcap"), "volume_24h": m.get("volume_24h"),
                     "rank": m.get("rank")})
    # rank by market cap when we have it, else by 24h volume, else keep config order
    rows.sort(key=lambda r: (r.get("rank") or 10 ** 6, -(r.get("mcap") or 0)))

    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(built), "series_len": SERIES_LEN,
               "rows": rows, "coins": built}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(built)} coins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
