#!/usr/bin/env python3
"""Insider and promoter trades (Task 8) - SAST and insider-trading disclosures."""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/insider.json"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

ENDPOINTS = {
    "pit": "https://www.nseindia.com/api/corporates-pit?index=equities",
    "sast": "https://www.nseindia.com/api/corporate-sast-reg29?index=equities",
}


def get(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  %s -> %s" % (url.split("?")[0].rsplit("/", 1)[-1], type(e).__name__))
        return None


def rows_of(data, kind):
    items = data.get("data") if isinstance(data, dict) else data
    out = []
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        low = {str(k).lower(): v for k, v in it.items()}
        sym = str(low.get("symbol") or low.get("scrip") or "").strip()
        if not sym:
            continue
        out.append([
            str(low.get("date") or low.get("intimdate") or low.get("acqfromdate") or "")[:10],
            sym,
            str(low.get("personname") or low.get("name") or low.get("acqname") or "").strip()[:40],
            str(low.get("category") or low.get("persontype") or kind).strip()[:24],
            str(low.get("buysell") or low.get("transactiontype") or "").strip().upper()[:8],
            str(low.get("secval") or low.get("value") or low.get("totacqvalue") or ""),
        ])
    return out


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "columns": ["Date", "Symbol", "Person", "Category", "Buy/Sell", "Value"],
           "rows": [], "note": "", "failed": []}
    for kind, url in ENDPOINTS.items():
        data = get(url)
        if data is None:
            out["failed"].append(kind)
            continue
        rows = rows_of(data, kind)
        out["rows"].extend(rows)
        print("  %s: %d rows" % (kind, len(rows)))
    out["rows"].sort(key=lambda r: r[0] or "", reverse=True)
    out["rows"] = out["rows"][:400]
    out["count"] = len(out["rows"])
    if not out["count"]:
        out["note"] = ("NSE's insider and SAST endpoints did not respond (%s). Nothing is shown "
                       "rather than a stale filing." % (", ".join(out["failed"]) or "empty payload"))
    else:
        out["note"] = ("Promoter and insider disclosures, newest first. Promoter buying is often "
                       "read as a positive signal; promoter selling is NOT automatically negative "
                       "- diversification, tax and family needs all produce sales. Both are shown "
                       "without implying a direction.")
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("insider: %d rows -> %s" % (out["count"], OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
