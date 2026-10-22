#!/usr/bin/env python3
"""Corporate actions and results calendar (Task 9).

Corporate actions come from this hub's own data (docs/data.json already carries the
dividends, splits and buybacks with their ex-dates). Board-meeting / results dates are
tried from NSE's event calendar and merged in when available.

Future dates go in the calendar; the last 30 days go in a separate "recent" list, because
a calendar that shows yesterday is confusing.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone, timedelta

OUT = "docs/calendar.json"
RECENT_DAYS = 30
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}
EVENTS = "https://www.nseindia.com/api/event-calendar?index=equities"


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def results_events():
    try:
        req = urllib.request.Request(EVENTS, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  event-calendar -> %s" % type(e).__name__)
        return []
    items = data.get("data") if isinstance(data, dict) else data
    out = []
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        low = {str(k).lower(): v for k, v in it.items()}
        sym = str(low.get("symbol") or "").strip()
        d = str(low.get("date") or low.get("exdate") or "").strip()
        purpose = str(low.get("purpose") or low.get("subject") or "Board meeting").strip()
        if not sym or not d:
            continue
        try:
            iso = datetime.strptime(d, "%d-%b-%Y").strftime("%Y-%m-%d")
        except Exception:
            iso = d[:10]
        out.append({"date": iso, "symbol": sym, "type": "results", "detail": purpose[:120]})
    print("  event-calendar: %d events" % len(out))
    return out


def main():
    today = datetime.now(timezone.utc).date()
    events = []
    d = load("docs/data.json")
    if d:
        co = d.get("corporate") or {}
        for key, label in (("dividend", "dividend"), ("split", "split"), ("other", "other")):
            bucket = co.get(key)
            rows = bucket.get("rows") if isinstance(bucket, dict) else bucket
            for r in (rows or []):
                try:
                    sym, subject, exd = r[0], r[1], r[2]
                except Exception:
                    continue
                if not exd:
                    continue
                events.append({"date": str(exd)[:10], "symbol": str(sym),
                               "type": label, "detail": str(subject)[:120]})
        print("  corporate actions from data.json: %d" % len(events))
    events.extend(results_events())

    future, recent = {}, {}
    for e in events:
        try:
            dd = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if dd >= today:
            future.setdefault(e["date"], []).append(e)
        elif (today - dd).days <= RECENT_DAYS:
            recent.setdefault(e["date"], []).append(e)

    def as_days(by_date):
        out = []
        for date in sorted(by_date):
            evs = sorted(by_date[date], key=lambda x: (x["type"], x["symbol"]))
            out.append({"date": date, "events": evs})
        return out

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "days": as_days(future), "recent": as_days(recent),
           "count": sum(len(v) for v in future.values()),
           "note": ""}
    if not out["count"] and not out["recent"]:
        out["note"] = "No corporate actions or results dates were available this run."
    else:
        out["note"] = ("Ex-dates and board meetings from today forward, plus the last %d days "
                       "separately. An ex-date is the first day the stock trades without the "
                       "dividend or split." % RECENT_DAYS)
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("calendar: %d future events over %d days -> %s" % (out["count"], len(out["days"]), OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
