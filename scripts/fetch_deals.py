#!/usr/bin/env python3
"""Bulk and block deals (Task 7).

A bulk deal is one client trading more than 0.5% of a company's equity; a block deal is a
negotiated trade above roughly Rs 10 crore. Both are disclosures, not recommendations.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/deals.json"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

ENDPOINTS = {
    "bulk": "https://www.nseindia.com/api/bulk-deal-archives",
    "block": "https://www.nseindia.com/api/block-deal-archives",
}


def get(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  %s -> %s" % (url.rsplit("/", 1)[-1], type(e).__name__))
        return None


def rows_of(data):
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("data") or data.get("DEALS") or []
    else:
        items = []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        low = {str(k).lower(): v for k, v in it.items()}
        out.append([
            str(low.get("date") or low.get("bdate") or "")[:10],
            str(low.get("symbol") or low.get("scrip") or "").strip(),
            str(low.get("clientname") or low.get("client") or "").strip()[:40],
            str(low.get("buysell") or low.get("buy_sell") or "").strip().upper(),
            str(low.get("qty") or low.get("quantity") or ""),
            str(low.get("price") or low.get("watp") or ""),
        ])
    return [r for r in out if r[1]]


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "columns": ["Date", "Symbol", "Client", "Buy/Sell", "Quantity", "Price"],
           "bulk": [], "block": [], "note": "", "failed": []}
    for key, url in ENDPOINTS.items():
        data = get(url)
        if data is None:
            out["failed"].append(key)
            continue
        out[key] = rows_of(data)[:400]
        print("  %s: %d rows" % (key, len(out[key])))
    out["count"] = len(out["bulk"]) + len(out["block"])
    if not out["count"]:
        out["note"] = ("NSE's deal archives did not respond (%s). Nothing is shown rather than "
                       "an empty table." % (", ".join(out["failed"]) or "empty payload"))
    else:
        out["note"] = ("Bulk deals are single-client trades above 0.5% of a company's equity; "
                       "block deals are negotiated trades above about Rs 10 crore. These are "
                       "disclosures, not recommendations - a large buy can be an index fund "
                       "rebalancing.")
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("deals: %d rows -> %s" % (out["count"], OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
