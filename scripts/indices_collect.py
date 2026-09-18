#!/usr/bin/env python3
"""
ALL INDIA INDICES — daily snapshot of every NSE index (139+) + BSE Sensex.

Sources (free, no keys):
  - NSE allIndices API  -> all NSE indices incl. Nifty 50, Bank, sector, VIX,
    market cap indices, strategy indices (with year high/low, PE, PB)
  - Yahoo chart API     -> BSE Sensex (^BSESN) as NSE API has no BSE indices

Output: data/indices-all.json  (self-healing: partial failures kept for next run)
"""
import json
import time
import datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "indices-all.json"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def nse_all_indices():
    out = []
    try:
        j = get_json("https://www.nseindia.com/api/allIndices")
        for d in j.get("data", []):
            if d.get("last") is None:
                continue
            out.append({
                "index": d.get("index"),
                "symbol": d.get("indexSymbol") or d.get("index"),
                "price": d.get("last"),
                "change": d.get("variation"),
                "change_pct": d.get("percentChange"),
                "year_high": d.get("yearHigh"),
                "year_low": d.get("yearLow"),
                "pe": d.get("pe"),
                "pb": d.get("pb"),
                "source": "NSE",
            })
    except Exception as e:  # noqa: BLE001
        print("WARN NSE allIndices failed:", e)
    return out


def yahoo_sensex():
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + quote("^BSESN") + "?range=1d&interval=1d")
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=25) as r:
                j = json.loads(r.read().decode())
            meta = j["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            if price and prev:
                return [{
                    "index": "BSE SENSEX",
                    "symbol": "^BSESN",
                    "price": round(price, 2),
                    "change": round(price - prev, 2),
                    "change_pct": round((price - prev) / prev * 100, 2),
                    "source": "Yahoo",
                }]
            return []
        except Exception:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
    return []


def main():
    rows = nse_all_indices()
    rows += yahoo_sensex()
    if not rows and OUT.exists():
        print("All sources failed — keeping previous snapshot")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(rows),
        "indices": rows,
    }, ensure_ascii=False, indent=1))
    print(f"indices-all: {len(rows)} indices snapshot written")


if __name__ == "__main__":
    main()
