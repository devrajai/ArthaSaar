#!/usr/bin/env python3
"""IPO tracker (Task 19) - mainboard and SME, kept separate.

NSE's IPO endpoints are undocumented and change shape. Every parse is defensive: if a
field is absent it is omitted, never guessed. If the endpoints are unreachable the file
is written with a `note` and the site shows that instead of a broken table.
"""
import json, os, sys, urllib.request, time
from datetime import datetime, timezone

OUT = "docs/ipo.json"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/all-upcoming-issues-ipo",
}
UPCOMING = "https://www.nseindia.com/api/all-upcoming-issues?category=ipo"
PAST = "https://www.nseindia.com/api/ipo-past-issues"


def get(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  %s -> %s" % (url.rsplit("/", 1)[-1], type(e).__name__))
        return None


def num(v):
    """NSE sometimes sends numbers, sometimes strings with commas. Return float or None."""
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def txt(v):
    return str(v).strip() if v not in (None, "") else ""


def is_sme(row):
    blob = " ".join(str(v) for v in row.values()).lower()
    return ("sme" in blob) or ("emerge" in blob)


def parse_dt(s):
    """NSE sends dates as 29-Oct-2026. Accept a few shapes and return None otherwise."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def norm_upcoming(d):
    rows = []
    items = d.get("data") if isinstance(d, dict) else d
    if isinstance(items, dict):
        items = items.get("data") or items.get("ipo") or []
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        name = txt(it.get("companyName") or it.get("symbol") or it.get("name"))
        if not name:
            continue
        rows.append({
            "name": name,
            "symbol": txt(it.get("symbol")),
            "open": txt(it.get("issueStartDate") or it.get("startDate")),
            "close": txt(it.get("issueEndDate") or it.get("endDate")),
            "band": txt(it.get("issuePrice") or it.get("priceBand")),
            "size": txt(it.get("issueSize") or it.get("totalIssueSize")),
            "status": txt(it.get("status") or it.get("issueStatus")),
            "sme": is_sme(it),
        })
    return rows


def norm_past(d):
    rows = []
    items = d.get("data") if isinstance(d, dict) else d
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        name = txt(it.get("companyName") or it.get("symbol") or it.get("name"))
        if not name:
            continue
        issue = num(it.get("issuePrice") or it.get("price"))
        listing = num(it.get("listingClose") or it.get("listingPrice") or it.get("closePrice"))
        gain = None
        if issue and listing and issue > 0:
            gain = round((listing - issue) / issue * 100.0, 2)
        rows.append({
            "name": name,
            "symbol": txt(it.get("symbol")),
            "issue_price": issue,
            "listing_price": listing,
            "listing_gain_pct": gain,
            "sme": is_sme(it),
        })
    return rows


def main():
    out = {
        "upcoming": [], "open": [], "closed": [], "listed": [],
        "mainboard": [], "sme": [], "note": "",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    up = get(UPCOMING)
    got = False
    if up is not None:
        got = True
        rows = norm_upcoming(up)

        # BUCKET BY DATE, NOT BY NSE'S STATUS WORDING.
        # NSE reports a currently-open issue as "Active" - a word containing neither
        # "open" nor "close". The old string matching therefore dropped every live IPO into
        # "upcoming", so the site showed 0 open while four were accepting bids, and the
        # section looked stale even though the dates were right.
        today = datetime.now(timezone.utc).date()
        for r in rows:
            o = parse_dt(r.get("open"))
            c = parse_dt(r.get("close"))
            st = (r.get("status") or "").lower()
            if o and c:
                if today < o:
                    bucket = "upcoming"
                elif o <= today <= c:
                    bucket = "open"
                else:
                    bucket = "closed"
            elif "active" in st or "open" in st:
                bucket = "open"
            elif "forthcoming" in st or "upcoming" in st:
                bucket = "upcoming"
            elif "close" in st:
                bucket = "closed"
            else:
                bucket = "upcoming"
            r["bucket"] = bucket
            out[bucket].append(r)
        out["mainboard"] = [r for r in rows if not r["sme"]]
        out["sme"] = [r for r in rows if r["sme"]]
        print("  upcoming: %d rows (%d mainboard, %d SME)" % (len(rows), len(out["mainboard"]), len(out["sme"])))

    past = get(PAST)
    if past is not None:
        got = True
        out["listed"] = norm_past(past)[:200]
        print("  listed: %d rows" % len(out["listed"]))

    # If the past-issues endpoint gave nothing, do not leave the tab empty - fall back to
    # issues that have closed and already carry a listing price. Better a shorter honest
    # list than a blank tab while listings plainly exist.
    if not out["listed"]:
        derived = [r for r in out["closed"] if r.get("listing_gain_pct") is not None]
        if derived:
            out["listed"] = derived[:200]
            print("  listed: %d rows (derived from closed issues with a listing price)"
                  % len(out["listed"]))

    out["count"] = len(out["upcoming"]) + len(out["open"]) + len(out["closed"]) + len(out["listed"])
    if not got:
        out["note"] = "NSE's IPO endpoints were unreachable from this network, so nothing is shown rather than something stale."
    elif not out["count"]:
        out["note"] = "NSE's IPO endpoints responded but carried no issues."

    os.makedirs("docs", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("ipo: %d rows -> %s" % (out["count"], OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
