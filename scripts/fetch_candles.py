#!/usr/bin/env python3
"""
fetch_candles.py — ArthaSaar Chart Reading data (Yahoo free, no API key).

Symbols:
  indices  : NIFTY, BANKNIFTY   -> 1m/5m/15m/1h
  F&O big  : RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS,
             SBIN, TATAMOTORS, ITC -> 5m/15m/1h

Output: data/candles.json  (column arrays — compact)
  { "updated": "...", "syms": { "NIFTY": { "y":"^NSEI", "pc": 23447.8,
      "1m": {"t":[..],"o":[..],"h":[..],"l":[..],"c":[..],"v":[..]}, ... } } }

Run:  python3 scripts/fetch_candles.py   (from repo root)
"""
import json
import os
import time
import datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 25

IDX = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
STOCKS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY",
          "TCS", "SBIN", "TATAMOTORS", "ITC"]

# interval -> yahoo range
RANGES = {"1m": "1d", "5m": "1d", "15m": "5d", "1h": "1mo"}
IDX_ONLY = {"1m"}  # 1m sirf indices (request budget)


def fetch(symbol, interval, rng, tries=4):
    path = ("/v8/finance/chart/" + symbol + f"?range={rng}&interval={interval}"
            + ("&includePrePost=false" if interval == "1m" else ""))
    last = None
    for a in range(tries):
        host = "query2" if a % 2 else "query1"
        try:
            req = Request("https://" + host + ".finance.yahoo.com" + path,
                          headers={"User-Agent": UA})
            with urlopen(req, timeout=TIMEOUT) as r:
                j = json.loads(r.read().decode())
            break
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2.5 * (a + 1))
    else:
        raise last or RuntimeError("fetch failed")
    res = j["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    ts = res.get("timestamp") or []
    out = {"t": [], "o": [], "h": [], "l": [], "c": [], "v": []}
    for i, t in enumerate(ts):
        o, h, l, c, v = (q["open"][i], q["high"][i], q["low"][i],
                         q["close"][i], q["volume"][i])
        if None in (o, h, l, c):
            continue
        out["t"].append(t)
        out["o"].append(round(float(o), 2))
        out["h"].append(round(float(h), 2))
        out["l"].append(round(float(l), 2))
        out["c"].append(round(float(c), 2))
        out["v"].append(int(v or 0))
    meta = res.get("meta", {})
    return out, (meta.get("chartPreviousClose")
                 or meta.get("previousClose"))


def main():
    root = Path(__file__).resolve().parents[1]
    data = {}
    old = {}
    try:
        old = json.loads((root / "data" / "candles.json")
                         .read_text(encoding="utf-8"))
        data = old.get("syms", {})
    except Exception:
        pass

    jobs = []
    for name, ysym in IDX.items():
        for iv in RANGES:
            jobs.append((name, ysym, iv))
    for s in STOCKS:
        for iv in ("5m", "15m", "1h"):
            jobs.append((s, s + ".NS", iv))

    for name, ysym, iv in jobs:
        try:
            bars, pc = fetch(ysym, iv, RANGES[iv])
            if not bars["t"]:
                raise ValueError("empty")
            entry = data.setdefault(name, {"y": ysym, "pc": None})
            entry[iv] = bars
            if pc:
                entry["pc"] = round(float(pc), 2)
            print(f"OK  {name} {iv}: {len(bars['t'])} bars")
        except Exception as e:  # noqa: BLE001
            print(f"SKIP {name} {iv}: {e}")
        time.sleep(0.7)

    out = {"updated": dt.datetime.now(
        dt.timezone(dt.timedelta(hours=5, minutes=30))
    ).strftime("%Y-%m-%dT%H:%M IST"),
        "syms": data}
    if not data:
        print("no data fetched — file not touched")
        return
    (root / "data").mkdir(parents=True, exist_ok=True)
    tmp = root / "data" / "candles.json"
    tmp.write_text(json.dumps(out, separators=(",", ":")),
                   encoding="utf-8")
    print("written", tmp, os.path.getsize(tmp), "bytes")


if __name__ == "__main__":
    main()
