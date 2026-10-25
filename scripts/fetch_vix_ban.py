#!/usr/bin/env python3
"""India VIX history, and the F&O ban list.

Both sources were TESTED before being built on, because NSE and friends move their file
addresses around:

  Yahoo ^INDIAVIX chart api ......... works (returned 14.06 14.77 15.68 15.76 16.86)
  nsearchives/content/fo/fo_secban.csv works (returned the 26-Oct-2026 ban list)
  nsearchives/content/fo/fo_mktlots.csv works (lot sizes, kept for ban-risk context)

  niftyindices.com .................. BLOCKED from the build sandbox - NOT used
  www.fpi.nsdl.co.in ................ BLOCKED from the build sandbox - NOT used
  fii_stats / fao_participant_oi .... 404 on every known naming pattern - NOT used

So FII index-futures positioning, Nifty PE/PB/DY and sector FPI flows are deliberately
absent rather than guessed at. Each is noted in the output so the site can say why.
"""
import json, os, sys, urllib.request, ssl
from datetime import datetime, timezone

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

VIX_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5EINDIAVIX?interval=1d&range=2y"
BAN_URL = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"


def get(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=timeout, context=CTX) as r:
            return r.read()
    except Exception as e:
        print("  %s -> %s" % (url.rsplit("/", 1)[-1][:40], type(e).__name__))
        return None


def vix():
    """Daily India VIX closes for the last two years."""
    body = get(VIX_URL)
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "series": [], "count": 0, "latest": None, "note": ""}
    if not body:
        out["note"] = "Yahoo did not return the India VIX series."
        return out
    try:
        res = json.loads(body)["chart"]["result"][0]
        ts = res.get("timestamp") or []
        cl = res["indicators"]["quote"][0].get("close") or []
    except Exception as e:
        out["note"] = "India VIX payload did not parse (%s)." % type(e).__name__
        return out
    for t, c in zip(ts, cl):
        if c is None:
            continue
        out["series"].append([datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"),
                              round(float(c), 2)])
    out["count"] = len(out["series"])
    if out["series"]:
        out["latest"] = out["series"][-1][1]
        vals = [v for _, v in out["series"]]
        out["low_2y"] = min(vals)
        out["high_2y"] = max(vals)
        # where today sits in the two-year range - the only thing most people want from VIX
        span = max(vals) - min(vals)
        out["percentile_2y"] = round((out["latest"] - min(vals)) / span * 100) if span else None
        out["note"] = ("India VIX is the NSE's 30-day implied volatility index, computed from "
                       "Nifty option prices. High means options are expensive and the market "
                       "expects big moves; low means it is complacent.")
    return out


def ban_list():
    """Securities currently banned from fresh F&O positions."""
    body = get(BAN_URL)
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "date": "", "symbols": [], "count": 0, "note": ""}
    if not body:
        out["note"] = "NSE's ban-list file did not respond."
        return out
    text = body.decode("utf-8", "replace").strip()
    if "<html" in text[:300].lower():
        out["note"] = "NSE returned an HTML page instead of the ban list."
        return out
    # the file is one line: "Securities in Ban For Trade Date 26-OCT-2026: 1,AMBUJACEM 2,KAYNES"
    head, _, rest = text.partition(":")
    out["date"] = head.replace("Securities in Ban For Trade Date", "").strip().rstrip(":")
    syms = []
    for chunk in rest.replace("\n", " ").split():
        part = chunk.split(",")
        if len(part) >= 2:
            syms.append(part[1].strip().upper())
        elif part[0].strip().isalpha() and len(part[0].strip()) > 1:
            syms.append(part[0].strip().upper())
    out["symbols"] = [s for s in syms if s and s != "NIL"]
    out["count"] = len(out["symbols"])
    out["note"] = ("These contracts have hit their market-wide position limit, so fresh "
                   "positions are banned until open interest falls. Existing positions can "
                   "only be reduced. A ban is a crowding signal, not a direction.")
    return out


def main():
    os.makedirs("docs", exist_ok=True)
    v = vix()
    json.dump(v, open("docs/vix.json", "w"), ensure_ascii=False)
    print("vix: %d points, latest %s -> docs/vix.json" % (v["count"], v.get("latest")))
    b = ban_list()
    json.dump(b, open("docs/fo_ban.json", "w"), ensure_ascii=False)
    print("fo ban: %d symbols for %s -> docs/fo_ban.json" % (b["count"], b["date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
