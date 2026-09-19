#!/usr/bin/env python3
"""
MARKET BRAIN — corporate filings collector (Phase 3).

Source: NSE /api/corporate-announcements (needs homepage cookie dance,
works from GitHub Actions runners). Every announcement published by every
listed company: quarterly results, AGM notices, board meetings, investor
presentations, shareholding, buybacks, etc. Each row carries a PDF link on
nsearchives.nseindia.com.

Filtering: Nifty 500 (tier 1) filings are kept in full; tier-2 items are
summarised by count. Output data/filings.json keeps the last 7 days,
deduped by attachment URL.

Category keywords classify each filing for the Notion "Company Filings"
database (Sarvam AI files the daily highlights there during the 18:30 IST
digest).
"""
import http.cookiejar
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
PAGES = 6          # ~1000 announcements per page batch
KEEP_DAYS = 7

CATS = [
    ("Results", r"result|financial results|financial performance"),
    ("AGM", r"\bagm\b|annual general meeting|annual report"),
    ("Board Meeting", r"board meeting|meeting of the board"),
    ("Investor Presentation", r"investor presentation|earnings call|conference call|presentation"),
    ("Shareholding", r"shareholding|share holding pattern"),
    ("Buyback / Dividend", r"buyback|buy-back|dividend|bonus|stock split|rights issue"),
    ("Fund Raise", r"fund rais|fundrais|qip|preferential issue|warrants"),
    ("Insider / Pledge", r"pledge|insider|promoter.*stake|acquisition.*shares"),
    ("Loan / Order Win", r"order win|order bagged|contract win|loan agreement|term loan|facility"),
    ("Credit Rating", r"credit rating|rating reassigned|rating action"),
]


def classify(subject):
    s = (subject or "").lower()
    for name, pat in CATS:
        if re.search(pat, s):
            return name
    return "Other"


def mk_session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA),
                     ("Accept", "text/html,application/xhtml+xml,*/*;q=0.8"),
                     ("Accept-Language", "en-US,en;q=0.9")]
    # cookie dance: homepage first, then an API ping to get nsit/bm cookies
    for url in ("https://www.nseindia.com/",
                "https://www.nseindia.com/api/marketStatus"):
        try:
            op.open(url, timeout=30).read(4096)
        except Exception as e:  # noqa: BLE001
            print(f"  session warmup: {url} -> {e}")
        time.sleep(1)
    return op


def fetch_announcements(op):
    out, seen = [], set()
    for page in range(1, PAGES + 1):
        url = f"https://www.nseindia.com/api/corporate-announcements?page={page}"
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": UA, "Accept": "application/json",
                                  "Referer": "https://www.nseindia.com/"})
                raw = op.open(req, timeout=30).read().decode("utf-8", "replace")
                d = json.loads(raw)
                rows = d.get("data", d) if isinstance(d, dict) else d
                if not isinstance(rows, list):
                    rows = []
                break
            except Exception as e:  # noqa: BLE001
                print(f"  page {page} attempt {attempt + 1}: {e}")
                time.sleep(5 * (attempt + 1))
                rows = None
                if attempt == 2:
                    return out
        if not rows:
            continue
        fresh = 0
        for r in rows:
            key = r.get("attchmntFile") or f"{r.get('symbol','')}-{r.get('seq_id','')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
            fresh += 1
        print(f"  page {page}: {len(rows)} rows, {fresh} new (total {len(out)})")
        if fresh == 0:
            break
        time.sleep(1.2)
    return out


def parse_date(s):
    # "19-Sep-2026 16:30:22" (IST) -> "2026-09-19"
    try:
        d = datetime.strptime(s.split(" ")[0], "%d-%b-%Y")
        return d.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


def main():
    DATA.mkdir(exist_ok=True)
    uni = {}
    try:
        for m in json.loads((DATA / "universe.json").read_text()):
            uni[m["symbol"]] = m
    except Exception:  # noqa: BLE001
        pass
    print(f"universe loaded: {len(uni)} symbols")

    op = mk_session()
    rows = fetch_announcements(op)
    print(f"announcements fetched: {len(rows)}")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    keep, tier2_count = [], 0
    for r in rows:
        d = parse_date(r.get("date", ""))
        if not d or d < cutoff:
            continue
        sym = r.get("symbol", "")
        item = {
            "symbol": sym,
            "company": uni.get(sym, {}).get("company") or r.get("sm_name", ""),
            "industry": uni.get(sym, {}).get("industry") or r.get("smIndustry", ""),
            "tier": uni.get(sym, {}).get("tier", 2),
            "date": d,
            "category": classify(r.get("subject", "")),
            "subject": (r.get("subject") or "")[:220],
            "pdf": r.get("attchmntFile"),
        }
        if item["tier"] == 1:
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
          f"({tier2_count} tier-2 skipped)")
    print("by category:", json.dumps(by_cat))


if __name__ == "__main__":
    main()
