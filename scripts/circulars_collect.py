#!/usr/bin/env python3
"""
ARTHASAAR - NSE exchange circulars collector (regulatory updates).

Source: NSE /api/circulars?index=equities (free; plain UA + Referer works).
This is the "hidden" regulatory layer brokers see first - Listing / Trading /
Compliance / Clearing circulars (band changes, margin, SLB, expiry, etc.).

Output: data/circulars.json  {"updated","source","count","items":[{date,cat,dept,no,co,pdf,subj}]}
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
API = "https://www.nseindia.com/api/circulars?index=equities"
REFERER = "https://www.nseindia.com/regulations/exchange-market-circulars"


def fetch():
    req = urllib.request.Request(API, headers={
        "User-Agent": UA, "Accept": "application/json, text/plain, */*",
        "Referer": REFERER, "Accept-Language": "en-US,en;q=0.9"})
    raw = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    d = json.loads(raw)
    return d.get("data") if isinstance(d, dict) else d


def main():
    DATA.mkdir(exist_ok=True)
    rows = []
    for attempt in range(3):
        try:
            rows = fetch() or []
            break
        except Exception as e:  # noqa: BLE001
            print(f"  attempt {attempt+1} failed: {e}")
    items = []
    for r in rows:
        items.append({
            "date": r.get("cirDisplayDate") or r.get("cirDate"),
            "cat": r.get("circCategory"),
            "dept": r.get("circDepartment"),
            "no": r.get("circDisplayNo"),
            "co": r.get("circCompany"),
            "pdf": r.get("circFilelink"),
            "subj": r.get("circDesc") or r.get("circSubject") or "",
        })
    (DATA / "circulars.json").write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "NSE exchange circulars",
        "count": len(items),
        "items": items,
    }, separators=(",", ":")))
    print(f"wrote {len(items)} circulars")


if __name__ == "__main__":
    main()
