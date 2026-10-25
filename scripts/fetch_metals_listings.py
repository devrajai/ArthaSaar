#!/usr/bin/env python3
"""Metals in rupees, and new listings / delistings.

SOURCES WERE TESTED BEFORE BUILDING, and the tests changed the design:

  Yahoo GC=F  (gold futures, USD/oz) ...... works  4007.90
  Yahoo SI=F  (silver futures, USD/oz) .... works  53.95
  Yahoo INR=X (USD/INR) ................... works  94.94
  nsearchives EQUITY_L.csv ................ works  has DATE OF LISTING -> 223 listings in
                                                   the last 3 months, newest 2026-10-23
  nsearchives delisted.csv ................ works BUT STALE: newest entry is 09-Nov-2020,
                                                   six years old. Kept as history, and the
                                                   output says so rather than implying it is
                                                   a current feed.
  nsearchives new_listed.csv .............. 404   - not used, EQUITY_L covers it

GOLD IN RUPEES IS APPROXIMATE AND SAYS SO. It is USD/oz x USD/INR at 31.1035 g per troy
ounce. It excludes import duty, GST, making charges and dealer premium, which in India add
roughly 15-20% on top. It is not a retail rate - it is the international metal converted,
which is what makes it useful for reading the trend.
"""
import csv, io, json, os, sys, urllib.request, ssl
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

TROY_OUNCE_G = 31.1035
EQUITY_L = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
DELISTED = "https://nsearchives.nseindia.com/content/equities/delisted.csv"


def get(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=timeout, context=CTX) as r:
            return r.read()
    except Exception as e:
        print("  %s -> %s" % (url.rsplit("/", 1)[-1][:36], type(e).__name__))
        return None


def yahoo_last(sym):
    """Last close from Yahoo's chart api, plus the prior close for a 1-day change."""
    import urllib.parse
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1d&range=1mo"
         % urllib.parse.quote(sym))
    b = get(u, 20)
    if not b:
        return None, None
    try:
        r = json.loads(b)["chart"]["result"][0]
        cl = [c for c in r["indicators"]["quote"][0]["close"] if c]
        if not cl:
            return None, None
        return float(cl[-1]), (float(cl[-2]) if len(cl) > 1 else None)
    except Exception:
        return None, None


def metals():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "gold": {}, "silver": {}, "usdinr": None, "note": ""}
    g, gprev = yahoo_last("GC=F")
    s, sprev = yahoo_last("SI=F")
    fx, _ = yahoo_last("INR=X")
    out["usdinr"] = round(fx, 2) if fx else None
    if g and fx:
        per_10g = g * fx / TROY_OUNCE_G * 10
        out["gold"] = {"usd_oz": round(g, 2), "inr_10g": round(per_10g),
                       "inr_gram": round(per_10g / 10),
                       "chg_pct": round((g / gprev - 1) * 100, 2) if gprev else None}
    if s and fx:
        # convert from the raw price, not from the already-rounded per-10g figure,
        # or the per-kg number drifts by a few rupees
        out["silver"] = {"usd_oz": round(s, 2),
                         "inr_10g": round(s * fx / TROY_OUNCE_G * 10),
                         "inr_kg": round(s * fx / TROY_OUNCE_G * 1000),
                         "chg_pct": round((s / sprev - 1) * 100, 2) if sprev else None}
    out["note"] = ("Approximate, converted from the international price. Excludes import "
                   "duty, GST and making charges, which add roughly 15-20% to what you "
                   "actually pay. Read the trend, do not price a purchase from it.")
    out["conversion"] = "USD per troy ounce x USD/INR, at %.4f g per troy ounce" % TROY_OUNCE_G
    return out


def parse_date(d):
    """NSE mixes formats; the delisted file uses dd-Mon-yy (e.g. 09-Nov-20)."""
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((d or "").strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def listings(months=3):
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "new": [], "delisted": [], "count_new": 0, "count_delisted": 0,
           "delisted_as_of": "", "note": ""}

    body = get(EQUITY_L)
    if body:
        # naive on purpose: strptime returns naive, and comparing naive to aware raises
        cutoff = datetime.utcnow() - timedelta(days=months * 31)
        rows = []
        for r in csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))):
            low = {str(k).strip().upper(): (v or "").strip() for k, v in r.items()}
            sym = low.get("SYMBOL") or ""
            dt = parse_date(low.get("DATE OF LISTING") or "")
            if not sym or not dt or dt < cutoff:
                continue
            rows.append([sym, low.get("NAME OF COMPANY", "")[:44],
                         dt.strftime("%Y-%m-%d"), low.get("SERIES", "")])
        rows.sort(key=lambda x: x[2], reverse=True)
        out["new"] = rows[:60]
        out["count_new"] = len(rows)

    body = get(DELISTED)
    if body:
        rows = []
        for r in csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))):
            low = {str(k).strip().lower(): (v or "").strip() for k, v in r.items()}
            sym = low.get("symbol") or ""
            if not sym:
                continue
            dt = parse_date(low.get("delisted date"))
            rows.append([sym, (low.get("company") or "")[:44],
                         dt.strftime("%Y-%m-%d") if dt else (low.get("delisted date") or ""),
                         low.get("type of delisting") or ""])
        # sort on the PARSED date. Sorting raw strings put "31-Mar-15" ahead of "2026-..."
        rows.sort(key=lambda x: x[2], reverse=True)
        out["delisted"] = rows[:60]
        out["count_delisted"] = len(rows)
        out["delisted_as_of"] = rows[0][2] if rows else ""

    out["note"] = ("New listings come from the listing date in NSE's symbol master and are "
                   "current. Delistings come from NSE's delisted-securities file, which has "
                   "NOT been updated since " + (out["delisted_as_of"] or "2020") +
                   " - treat that list as history, not a current feed. A delisting is also "
                   "not always bad: mergers and scheme amalgamations appear here too.")
    return out


def main():
    os.makedirs("docs", exist_ok=True)
    m = metals()
    json.dump(m, open("docs/metals.json", "w"), ensure_ascii=False)
    print("metals: gold %s/10g, silver %s/kg, USD/INR %s -> docs/metals.json"
          % (m["gold"].get("inr_10g"), m["silver"].get("inr_kg"), m["usdinr"]))
    l = listings()
    json.dump(l, open("docs/listings.json", "w"), ensure_ascii=False)
    print("listings: %d new, %d delisted (file stops %s) -> docs/listings.json"
          % (l["count_new"], l["count_delisted"], l["delisted_as_of"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
