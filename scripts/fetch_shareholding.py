#!/usr/bin/env python3
"""Promoter pledge and shareholding (Task 18).

How much of a company the promoters hold, and how much of that is pledged, quarter by
quarter. A RISING pledge next to a falling price is the thing worth seeing.

NSE's shareholding endpoint is undocumented and frequently unavailable. This script is
defensive throughout: if the source is unreachable the file is written with a `note` and
the site shows that. It never substitutes a guessed figure - a wrong pledge number is
worse than a blank.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/shareholding.json"
MASTER = "https://www.nseindia.com/api/corporate-share-holdings-master?index=equities"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
}
QUARTERS = 4


def get(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  shareholding -> %s" % type(e).__name__)
        return None


def fnum(v):
    if v is None or v == "":
        return None
    try:
        return round(float(str(v).replace(",", "").replace("%", "").strip()), 2)
    except Exception:
        return None


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": [], "count": 0, "quarters": QUARTERS, "note": ""}
    data = get(MASTER)
    if data is None:
        out["note"] = ("NSE's shareholding endpoint was unreachable from this network. "
                       "Nothing is shown rather than a stale or guessed pledge figure.")
    else:
        items = data.get("data") if isinstance(data, dict) else data
        for it in (items or []):
            if not isinstance(it, dict):
                continue
            sym = str(it.get("symbol") or "").strip()
            if not sym:
                continue
            q = str(it.get("date") or it.get("quarter") or it.get("qtr") or "").strip()
            prom = fnum(it.get("promoterAndPromoterGroup") or it.get("promoter"))
            pledge = fnum(it.get("pledgedPercentageInPromoter")
                          or it.get("pledgedPercentage")
                          or it.get("promoterPledge"))
            if prom is None and pledge is None:
                continue
            out["rows"].append({"symbol": sym, "q": q, "promoter": prom, "pledge": pledge})
        out["count"] = len(out["rows"])
        if not out["count"]:
            out["note"] = ("NSE's endpoint responded but the payload had no promoter figures "
                           "this run, so the tab is empty rather than misleading.")
        else:
            out["note"] = ("Promoter holding and pledge, newest quarter first. A pledge is not "
                           "automatically bad, but a RISING pledge beside a falling price "
                           "deserves attention.")

    os.makedirs("docs", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("shareholding: %d rows -> %s" % (out["count"], OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
