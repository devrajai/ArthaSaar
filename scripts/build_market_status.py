#!/usr/bin/env python3
"""Market session status and holidays (Task 5).

The open/closed decision is made in the BROWSER, not here, so it stays correct all day.
This script only publishes the session times and the holiday list.

NSE's holiday endpoint is undocumented. If it fails, a hand-maintained
config/market_holidays.json is used instead, and the output says which was used.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/market_status.json"
FALLBACK = "config/market_holidays.json"
API = "https://www.nseindia.com/api/holiday-master?type=trading"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "application/json, text/plain, */*",
      "Referer": "https://www.nseindia.com/"}


def from_api():
    try:
        req = urllib.request.Request(API, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  holiday API -> %s" % type(e).__name__)
        return None
    out = []
    for group in (data.get("CM") or data.get("FO") or []):
        if not isinstance(group, dict):
            continue
        d = str(group.get("tradingDate") or "").strip()
        desc = str(group.get("description") or "").strip()
        if not d:
            continue
        try:
            iso = datetime.strptime(d, "%d-%b-%Y").strftime("%Y-%m-%d")
        except Exception:
            iso = d
        if iso and (not out or out[-1][0] != iso):
            out.append([iso, desc])
    return out or None


def from_file():
    try:
        data = json.load(open(FALLBACK))
        return [[h[0], h[1]] for h in (data.get("holidays") or []) if h]
    except Exception:
        return None


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "timezone": "Asia/Kolkata", "open": "09:15", "close": "15:30",
           "preopen": "09:00", "holidays": [], "source": "", "note": ""}
    h = from_api()
    if h:
        out["source"] = "NSE holiday-master API"
    else:
        h = from_file()
        if h:
            out["source"] = "config/market_holidays.json (hand-maintained fallback)"
        else:
            out["source"] = "none"
    out["holidays"] = h or []
    if not out["holidays"]:
        out["note"] = ("The holiday list could not be fetched and no fallback file exists, so "
                       "the session chip uses weekdays only. It will read Open on a holiday.")
    else:
        out["note"] = ("Session times are IST. Whether the market is open is worked out in the "
                       "browser from these times and this holiday list, so it stays correct "
                       "through the day. Source: %s." % out["source"])
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("market status: %d holidays (%s)" % (len(out["holidays"]), out["source"]))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
