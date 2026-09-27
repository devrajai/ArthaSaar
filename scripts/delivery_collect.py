#!/usr/bin/env python3
"""delivery_collect.py - NSE bhavcopy delivery % -> data/delivery.json
Free source: archives.nseindia.com sec_bhavdata_full (published ~evening IST).
Screener "D%" column (dlvfix.js) reads this file. If fetch fails, old file kept.
"""
import csv
import io
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,*/*",
    "Referer": "https://www.nseindia.com/",
}
KEEP_SERIES = ("EQ", "BE", "BZ")


def fetch_day(d):
    url = "https://archives.nseindia.com/products/content/sec_bhavdata_full_%s.csv" % d.strftime("%d%m%Y")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        data = r.read().decode("utf-8", "ignore")
    if "<html" in data[:500].lower() or len(data) < 200:
        raise RuntimeError("not a csv / too small")
    return data


def parse(csv_text):
    out = {}
    rd = csv.DictReader(io.StringIO(csv_text), skipinitialspace=True)
    for row in rd:
        sym = (row.get("SYMBOL") or "").strip().upper()
        ser = (row.get("SERIES") or "").strip().upper()
        if not sym or ser not in KEEP_SERIES:
            continue
        try:
            dpv = float((row.get("DELIV_PER") or "").strip())
        except ValueError:
            continue
        out[sym] = round(dpv, 1)
    return out


def main():
    today = datetime.now(IST).date()
    last_err = "no trading day tried"
    for back in range(0, 5):
        d = today - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        try:
            txt = fetch_day(d)
            data = parse(txt)
            if not data:
                last_err = "empty parse %s" % d
                continue
            out = {
                "date": d.isoformat(),
                "n": len(data),
                "updated": datetime.now(IST).strftime("%d %b %Y, %H:%M IST"),
                "d": data,
            }
            os.makedirs("data", exist_ok=True)
            with open("data/delivery.json", "w") as f:
                json.dump(out, f, separators=(",", ":"))
            print("delivery.json:", len(data), "symbols for", d)
            return
        except Exception as e:
            last_err = str(e)[:80]
            print("retry", d, last_err)
    if not os.path.exists("data/delivery.json"):
        out = {"date": None, "n": 0, "updated": "no data yet", "d": {}}
        os.makedirs("data", exist_ok=True)
        with open("data/delivery.json", "w") as f:
            json.dump(out, f, separators=(",", ":"))
    print("WARN: no bhavcopy fetched:", last_err)


if __name__ == "__main__":
    main()