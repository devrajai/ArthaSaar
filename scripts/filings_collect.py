#!/usr/bin/env python3
"""
MARKET BRAIN — corporate filings collector (Phase 3).

Source: NSE /api/corporate-announcements?index=equities&from_date=D-M-Y&to_date=D-M-Y
(verified 19/09/26: works from datacenter IPs with plain UA + Referer, no
cookies; a 7-day window returns ~2,300 announcements in ONE call).
Every announcement published by every listed company: quarterly results,
AGM notices, board meetings, investor presentations, shareholding,
buybacks, etc. Each row carries a PDF link on nsearchives.nseindia.com.

Filtering: Nifty 500 (tier 1) filings in meaningful categories are kept
('Other' + tier-2 are counted, not stored). data/filings.json keeps the
last KEEP_DAYS days.

Category comes from NSE's own `desc` field, mapped to friendly buckets for
the Notion "Company Filings" database (Sarvam AI files the daily
highlights there during the 18:30 IST digest).
"""
import json
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
API = ("https://www.nseindia.com/api/corporate-announcements"
       "?index=equities&from_date={from_d}&to_date={to_d}")
REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
KEEP_DAYS = 7

CATS = [
    ("AGM", r"\bagm\b|annual general meeting|annual report|voting result|scrutinizer|postal ballot|proceedings of annual"),
    ("Results", r"result|financial performance"),
    ("Board Meeting", r"board meeting|meeting of the board"),
    ("Investor Presentation", r"investor presentation|earnings call|conference call|presentation"),
    ("Shareholding", r"shareholding|share holding pattern"),
    ("Buyback / Dividend", r"buyback|buy-back|dividend|bonus|stock split|rights issue"),
    ("Fund Raise", r"fund rais|fundrais|qip|preferential issue|warrants"),
    ("Insider / Pledge", r"pledge|insider|promoter.*stake|acquisition.*shares"),
    ("Loan / Order Win", r"order win|order bagged|contract win|loan agreement|term loan|facility"),
    ("Credit Rating", r"credit rating|rating reassigned|rating action"),
]


def classify(desc, text):
    for source in (desc or "", text or ""):
        s = source.lower()
        for name, pat in CATS:
            if re.search(pat, s):
                return name
    return "Other"


def fetch_window(from_d, to_d):
    """Full announcement list for a date range (dd-mm-yyyy), one call."""
    req = urllib.request.Request(
        API.format(from_d=from_d, to_d=to_d),
        headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                 "Referer": REFERER, "Accept-Language": "en-US,en;q=0.9"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    rows = json.loads(raw)
    return rows if isinstance(rows, list) else []


def main():
    DATA.mkdir(exist_ok=True)
    uni = {}
    try:
        for m in json.loads((DATA / "universe.json").read_text()):
            uni[m["symbol"]] = m
    except Exception:  # noqa: BLE001
        pass
    print(f"universe loaded: {len(uni)} symbols")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    to_d = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    from_d = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%d-%m-%Y")
    out = []
    for attempt in range(3):
        try:
            out = fetch_window(from_d, to_d)
            break
        except Exception as e:  # noqa: BLE001
            print(f"  fetch attempt {attempt + 1} failed: {e}")
            time.sleep(10 * (attempt + 1))
    print(f"  fetched {len(out)} announcements for window {from_d} -> {to_d}")

    keep, tier2_count = [], 0
    for r in out:
        d = (r.get("sort_date") or "")[:10]
        if not d or d < cutoff:
            continue
        sym = r.get("symbol", "")
        item = {
            "symbol": sym,
            "company": uni.get(sym, {}).get("company") or r.get("sm_name", ""),
            "industry": uni.get(sym, {}).get("industry") or r.get("smIndustry", ""),
            "tier": uni.get(sym, {}).get("tier", 2),
            "date": d,
            "category": classify(r.get("desc"), r.get("attchmntText")),
            "nse_desc": r.get("desc", ""),
            "subject": (r.get("attchmntText") or "")[:220],
            "pdf": r.get("attchmntFile"),
        }
        if item["tier"] == 1 and item["category"] != "Other":
            keep.append(item)
        else:
            tier2_count += 1

    keep.sort(key=lambda x: (x["date"], x["symbol"]), reverse=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "window_days": KEEP_DAYS,
        "tier1_filings": len(keep),
        "tier2_count": tier2_count,
        "filings": keep,
    }
    (DATA / "filings.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1))
    by_cat = {}
    for f in keep:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    print(f"filings.json written: {len(keep)} tier-1 filings "
          f"({tier2_count} tier-2/other skipped)")
    print("by category:", json.dumps(by_cat))


if __name__ == "__main__":
    main()
