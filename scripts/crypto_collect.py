#!/usr/bin/env python3
"""
MARKET BRAIN — crypto watch collector (Phase 4).

Free sources, no keys:
  1. CoinGecko public API (primary):
     - /global  -> total market cap, BTC/ETH dominance, 24h mcap change
     - /coins/markets (top 100 by market cap) -> price, 24h/7d/30d change,
       market cap, volume, distance from ATH
  2. Binance public API (fallback if CoinGecko rate-limits):
     - /api/v3/ticker/24hr -> USDT pairs ranked by quote volume
  3. alternative.me Fear & Greed Index (optional, non-fatal)

Output: data/crypto.json — feeds the daily digest + future website.
Runs on GitHub Actions (crypto APIs are unreachable from some datacenter
sandboxes, so this script is verified on the runner itself).
"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TOP = 100
LEVERAGED = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def get_json(url, timeout=30):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout)
                      .read().decode("utf-8", "replace"))


def try_get(url, tries=3):
    for i in range(tries):
        try:
            return get_json(url)
        except Exception as e:  # noqa: BLE001
            print(f"  {url.split('?')[0].split('/api')[-1]} attempt {i+1}: {e}")
            time.sleep(3 * (i + 1))
    return None


def coingecko():
    g = try_get("https://api.coingecko.com/api/v3/global")
    coins = try_get("https://api.coingecko.com/api/v3/coins/markets"
                    "?vs_currency=usd&order=market_cap_desc"
                    f"&per_page={TOP}&page=1"
                    "&price_change_percentage=24h,7d,30d")
    if not coins:
        return None
    top = [{
        "rank": c.get("market_cap_rank"),
        "symbol": (c.get("symbol") or "").upper(),
        "name": c.get("name", ""),
        "price_usd": c.get("current_price"),
        "chg_24h_pct": round(c["price_change_percentage_24h_in_currency"], 2)
        if c.get("price_change_percentage_24h_in_currency") is not None else None,
        "chg_7d_pct": round(c["price_change_percentage_7d_in_currency"], 2)
        if c.get("price_change_percentage_7d_in_currency") is not None else None,
        "chg_30d_pct": round(c["price_change_percentage_30d_in_currency"], 2)
        if c.get("price_change_percentage_30d_in_currency") is not None else None,
        "market_cap": c.get("market_cap"),
        "volume_usd": c.get("total_volume"),
        "from_ath_pct": round(c["ath_change_percentage"], 1)
        if c.get("ath_change_percentage") is not None else None,
    } for c in coins]
    glob = {}
    if g:
        d = g.get("data", {})
        glob = {
            "total_market_cap_usd": d.get("total_market_cap", {}).get("usd"),
            "total_volume_usd": d.get("total_volume", {}).get("usd"),
            "btc_dominance": round(d.get("market_cap_percentage", {})
                                    .get("btc", 0), 1),
            "eth_dominance": round(d.get("market_cap_percentage", {})
                                    .get("eth", 0), 1),
            "mcap_chg_24h_pct": round(d.get(
                "market_cap_change_percentage_24h_usd", 0), 1),
        }
    return glob, top, "coingecko"


def binance():
    t = try_get("https://api.binance.com/api/v3/ticker/24hr")
    if not t:
        return None
    usdt = [x for x in t if x["symbol"].endswith("USDT")
            and not any(x["symbol"].endswith(l) for l in LEVERAGED)]
    usdt.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)
    top = [{
        "rank": i + 1,
        "symbol": x["symbol"][:-4],
        "name": x["symbol"][:-4],
        "price_usd": float(x["lastPrice"]),
        "chg_24h_pct": float(x["priceChangePercent"]),
        "chg_7d_pct": None,
        "chg_30d_pct": None,
        "market_cap": None,
        "volume_usd": float(x["quoteVolume"]),
        "from_ath_pct": None,
    } for i, x in enumerate(usdt[:TOP])]
    return {}, top, "binance"


def fear_greed():
    try:
        f = get_json("https://api.alternative.me/fng/?limit=1")
        d = f["data"][0]
        return {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception:  # noqa: BLE001
        return None


def main():
    DATA.mkdir(exist_ok=True)
    res = coingecko() or binance()
    if not res:
        print("FATAL: no crypto source reachable")
        return
    glob, top, source = res
    fg = fear_greed()

    gainers = sorted([c for c in top if c["chg_24h_pct"] is not None],
                     key=lambda c: c["chg_24h_pct"], reverse=True)[:10]
    losers = sorted([c for c in top if c["chg_24h_pct"] is not None],
                    key=lambda c: c["chg_24h_pct"])[:10]

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "global": glob,
        "fear_greed": fg,
        "top": top,
        "gainers_24h": gainers,
        "losers_24h": losers,
    }
    (DATA / "crypto.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1))
    btc = next((c for c in top if c["symbol"] == "BTC"), None)
    print(f"crypto.json written via {source}: {len(top)} coins | "
          + (f"BTC ${btc['price_usd']:,.0f} ({btc['chg_24h_pct']:+.1f}% 24h) "
             if btc else "")
          + (f"| F&G {fg['value']} {fg['label']}" if fg else "| F&G n/a"))


if __name__ == "__main__":
    main()
