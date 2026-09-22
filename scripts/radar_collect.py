#!/usr/bin/env python3
"""radar_collect.py - Operator Radar: delivery % scanner (NSE sec_bhavdata).
High delivery % + volume = accumulation (whale khareed raha hai).
Output: data/radar.json"""
import csv
import io
import json
import os
import urllib.request
from datetime import date, datetime, timedelta

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def fetch():
    for back in range(0, 5):
        d = date.today() - timedelta(days=back)
        if d.weekday() >= 5 and back == 0:
            continue
        url = ("https://nsearchives.nseindia.com/products/content/"
               f"sec_bhavdata_full_{d:%d%m%Y}.csv")
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", "ignore")
            return d, list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            print(f"no bhavdata {d}: {e}")
    return None, None

def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0

def main():
    d, rows = fetch()
    if not rows:
        print("ERROR: no bhavdata"); raise SystemExit(1)
    stocks = []
    for r in rows:
        ser = (r.get(" SERIES") or r.get("SERIES") or "").strip()
        if ser != "EQ":
            continue
        sym = r.get("SYMBOL", "").strip()
        close = num(r.get(" CLOSE_PRICE") or r.get("CLOSE_PRICE"))
        prev = num(r.get(" PREV_CLOSE") or r.get("PREV_CLOSE"))
        tover = num(r.get(" TURNOVER_LACS") or r.get("TURNOVER_LACS"))
        dper = num(r.get(" DELIV_PER") or r.get("DELIV_PER"))
        if not sym or close <= 0 or prev <= 0:
            continue
        chg = round((close - prev) / prev * 100, 2)
        stocks.append({"sym": sym, "close": close, "chg": chg,
                       "deliv": round(dper, 1), "tover_l": round(tover, 0)})
    liquid = [s for s in stocks if s["tover_l"] > 500]
    acc = sorted([s for s in liquid if s["chg"] > 0], key=lambda s: s["deliv"], reverse=True)[:15]
    dist = sorted([s for s in liquid if s["chg"] <= -1], key=lambda s: s["deliv"], reverse=True)[:10]
    vol = sorted([s for s in liquid if abs(s["chg"]) > 2], key=lambda s: s["tover_l"], reverse=True)[:10]
    out = {"updated": datetime.now().isoformat(), "date": d.strftime("%d-%m-%Y"),
           "accumulation": acc, "hidden_selling": dist, "volume_blast": vol,
           "note": "Delivery % NSE EOD se. High delivery + green = whale accumulation. High delivery + red = dhire dhire bech raha hai."}
    os.makedirs("data", exist_ok=True)
    with open("data/radar.json", "w") as f:
        json.dump(out, f, indent=1)
    print("radar.json:", len(acc), "acc /", len(dist), "dist /", len(vol), "vol |", len(stocks), "EQ stocks")

if __name__ == "__main__":
    main()
