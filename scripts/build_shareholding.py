#!/usr/bin/env python3
"""Promoter holding, free float, and index membership - the input to any weight calculation.

WHY THIS MATTERS
The shareholding tab has been empty for weeks, and the review named it as the one data source
that unlocks index weights, points contribution and a passive-inflow estimate. This fetches it
from NSE's own filing master.

WHAT IT GETS
  pr_and_prgrp   promoter and promoter group holding, percent
  public_val     public holding, percent
  date           the quarter the filing covers
  index lists    Nifty 50, Nifty Bank and Nifty 500 membership

WHAT IT CANNOT GET, AND WHY THE WEIGHT IS NOT PUBLISHED
A Nifty weight is free-float market cap divided by the total of the index. That needs THREE
inputs:

  promoter holding      available here
  free float            derived here as 100 - promoter, which is close but not exact - NSE
                        also excludes government holdings, ADR/GDR and locked-in stakes
  SHARES OUTSTANDING    not available. NSE's quote API returns 403 without a browser session,
                        Yahoo's quote and quoteSummary endpoints return 401, and the index
                        constituent files carry membership only, with no share count.

Without shares outstanding there is no market cap, and without market cap there is no weight.
Publishing a weight derived from a guess would look precise and be wrong - which is worse than
showing membership and free float, which are exact.

WHAT THIS DOES GIVE
  * whether a stock is in the index at all (Jio Platforms is not, so its weight is zero)
  * the promoter stake and the public float, both from the filing
  * the free-float percentage, which is the largest single input to the weight
"""
import csv, io, json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/shareholding.json"
SH_URL = ("https://www.nseindia.com/api/corporate-share-holdings-master"
          "?index=equities&from_date=01-01-2026&to_date=31-12-2026")
INDEX_FILES = [
    ("NIFTY50", "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"),
    ("NIFTYBANK", "https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv"),
    ("NIFTY500", "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"),
]
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_shareholding():
    try:
        raw = urllib.request.urlopen(urllib.request.Request(SH_URL, headers=UA), timeout=120).read()
        return json.loads(raw)
    except Exception as e:
        print("  shareholding fetch failed: %s: %s" % (type(e).__name__, str(e)[:80]))
        return []


def fetch_index():
    """symbol -> list of index names it belongs to."""
    member = {}
    for name, url in INDEX_FILES:
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            txt = raw.decode("utf-8", "replace")
            for row in csv.DictReader(io.StringIO(txt)):
                sym = (row.get("Symbol") or "").strip().upper()
                if sym:
                    member.setdefault(sym, []).append(name)
            print("  %-10s %d constituents" % (name, sum(1 for v in member.values() if name in v)))
        except Exception as e:
            print("  %-10s failed: %s" % (name, type(e).__name__))
    return member


def main():
    out = {"updated": now(), "count": 0, "rows": [], "index_membership": {},
           "note": "", "cautions": {}}

    print("fetching shareholding filings ...")
    records = fetch_shareholding()
    print("  %d filing records" % len(records))

    print("fetching index constituent lists ...")
    member = fetch_index()
    out["index_membership"] = {k: v for k, v in sorted(member.items())}

    if not records:
        out["note"] = ("NSE's shareholding master could not be fetched this run. The tab stays "
                       "empty rather than showing stale figures.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print("shareholding: nothing fetched")
        return 0

    # keep the LATEST filing per symbol - the master returns several quarters
    latest = {}
    for r in records:
        sym = str(r.get("symbol") or "").strip().upper()
        if not sym:
            continue
        d = str(r.get("date") or "")
        # dates look like 30-SEP-2026
        try:
            key = datetime.strptime(d, "%d-%b-%Y").date()
        except Exception:
            key = datetime.min.date()
        if sym not in latest or key > latest[sym][0]:
            latest[sym] = (key, r)

    rows = []
    for sym, (dt_, r) in latest.items():
        try:
            prom = float(r.get("pr_and_prgrp"))
        except Exception:
            continue
        pub = r.get("public_val")
        try:
            pub = float(pub) if pub not in (None, "") else None
        except Exception:
            pub = None
        rows.append({
            "symbol": sym,
            "name": (r.get("name") or "")[:44],
            "as_of": str(r.get("date")),
            "promoter_pct": round(prom, 2),
            "public_pct": round(pub, 2) if pub is not None else None,
            # free float is approximately everything the promoter does not hold. It is a
            # close proxy, not NSE's exact factor, which also strips government stakes,
            # ADR/GDR and lock-ins.
            "free_float_proxy_pct": round(100 - prom, 2),
            "in_indices": member.get(sym, []),
        })

    rows.sort(key=lambda x: -x["promoter_pct"])
    out["rows"] = rows
    out["count"] = len(rows)
    out["with_index"] = sum(1 for r in rows if r["in_indices"])
    out["note"] = ("Promoter and public holding from NSE's shareholding filing master, latest "
                   "quarter per company, plus index membership. %d companies, %d of them in a "
                   "major index." % (len(rows), out["with_index"]))
    out["cautions"] = {
        "no_weights": ("Index WEIGHTS and points contributed are deliberately not published. "
                       "A weight needs free-float market cap, which needs SHARES OUTSTANDING - "
                       "and no free source here provides it: NSE's quote API returns 403 "
                       "without a browser session, Yahoo's quote endpoints return 401, and the "
                       "index files carry membership only. Membership and free float are exact; "
                       "a weight would be a guess dressed as a number."),
        "free_float_is_a_proxy": ("free_float_proxy_pct is 100 minus the promoter stake. NSE's "
                                  "own factor also removes government holdings, ADR/GDR and "
                                  "locked-in shares, so the true float is usually somewhat "
                                  "lower."),
        "quarterly": ("Shareholding is filed quarterly, so a row can be up to three months old. "
                      "The filing date is shown on every row."),
        "revisions": ("Some companies revise earlier filings. Only the latest date per symbol "
                      "is kept, so a revision that arrives late replaces the original."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d companies | %d in a major index" % (out["count"], out["with_index"]))
    for r in rows[:5]:
        print("     %-12s promoter %5.2f%%  float %5.2f%%  %s"
              % (r["symbol"], r["promoter_pct"], r["free_float_proxy_pct"],
                 ",".join(r["in_indices"]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
